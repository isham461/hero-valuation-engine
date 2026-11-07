"""PS1 Valuation Engine — Model Training & Evaluation (v2)
Improvements:
  - 14 features (log_sqft, log_sqft_per_bhk, locality_median_ppsqft, no dead is_high_floor)
  - LightGBM tuned with 1000 trees, lr=0.03, num_leaves=63, reg_lambda=3.0, reg_alpha=0.5
  - Quantiles at 0.08 and 0.92 for wider, more reliable coverage
  - Produces valuation_bundle_v2.pkl and evaluation_metrics_v2.json
"""
from __future__ import annotations

import hashlib
import json
import platform
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from backend.features_v2 import (
    AUTO_ACCEPT_MAX_RELATIVE_WIDTH, AUTO_ACCEPT_MIN_LOCALITY_SAMPLES, FEATURE_COLS,
    auto_accept_mask, build_features, build_locality_lookup, normalize_key,
    ordered_interval, predict_valuation, resolve_context, with_keys,
)

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"
SEED = 42
MODEL_PARAMS = {
    "n_estimators": 1000, "learning_rate": 0.03, "num_leaves": 63,
    "min_child_samples": 50, "reg_lambda": 3.0, "reg_alpha": 0.5,
    "subsample": 0.85, "subsample_freq": 1, "colsample_bytree": 0.85,
    "random_state": SEED, "n_jobs": 4, "verbosity": -1,
    "deterministic": True, "force_col_wise": True,
}
QUANTILE_LOW = 0.08
QUANTILE_HIGH = 0.92


def locality_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    train, test = with_keys(train), with_keys(test)
    rates = train.groupby(["city_key", "locality_key"])["price_per_sqft"].median()
    keys = pd.MultiIndex.from_frame(test[["city_key", "locality_key"]])
    locality_rates = pd.Series(rates.reindex(keys).to_numpy(), index=test.index)
    city_rates = test["city_key"].map(train.groupby("city_key")["price_per_sqft"].median())
    resolved = locality_rates.fillna(city_rates).fillna(train["price_per_sqft"].median())
    return resolved.to_numpy() * test["sqft"].to_numpy() / 100000


def ridge_model():
    return make_pipeline(StandardScaler(), Ridge(alpha=10.0))


def fit_baselines(train: pd.DataFrame, test: pd.DataFrame, X_train: pd.DataFrame, X_test: pd.DataFrame):
    target = np.log(train["price_lakhs"].to_numpy())
    oof = {"Locality median sqft rate": np.empty(len(train)), "Ridge regression": np.empty(len(train))}
    for fit_indices, validation_indices in KFold(n_splits=5, shuffle=True, random_state=SEED).split(train):
        fit, validation = train.iloc[fit_indices], train.iloc[validation_indices]
        oof["Locality median sqft rate"][validation_indices] = locality_baseline(fit, validation)
        ridge = ridge_model().fit(X_train.iloc[fit_indices], target[fit_indices])
        oof["Ridge regression"][validation_indices] = np.exp(ridge.predict(X_train.iloc[validation_indices]))
    ridge = ridge_model().fit(X_train, target)
    predictions = {
        "Locality median sqft rate": locality_baseline(train, test),
        "Ridge regression": np.exp(ridge.predict(X_test)),
    }
    result = {}
    for name, point in predictions.items():
        log_residuals = target - np.log(oof[name])
        q10, q90 = np.quantile(log_residuals, [QUANTILE_LOW, QUANTILE_HIGH])
        low, high = ordered_interval(point, point * np.exp(q10), point * np.exp(q90))
        result[name] = (point, low, high)
    return result


def train_lightgbm(X: pd.DataFrame, y: np.ndarray) -> dict:
    models = {}
    for name, objective, alpha in (
        ("model_point", "regression_l1", None),
        ("model_low", "quantile", QUANTILE_LOW),
        ("model_high", "quantile", QUANTILE_HIGH),
    ):
        params = dict(MODEL_PARAMS, objective=objective)
        if alpha is not None:
            params["alpha"] = alpha
        models[name] = LGBMRegressor(**params).fit(X, np.log(y))
    return models


def evaluate(y, point, low, high, support) -> dict:
    y, point = np.asarray(y), np.asarray(point)
    if not np.isfinite(np.column_stack([point, low, high])).all() or np.any(point <= 0):
        raise ValueError("Model produced invalid predictions")
    errors = np.abs(y - point) / y
    accepted = auto_accept_mask(point, low, high, support)
    return {
        "n_test": len(y), "mdape_pct": float(np.median(errors) * 100),
        "within_10_pct": float(np.mean(errors <= 0.10) * 100),
        "within_20_pct": float(np.mean(errors <= 0.20) * 100),
        "auto_accept_pct": float(np.mean(accepted) * 100),
        "auto_accept_count": int(accepted.sum()),
        "accepted_within_20_pct": float(np.mean(errors[accepted] <= 0.20) * 100) if accepted.any() else None,
        "interval_coverage_pct": float(np.mean((y >= low) & (y <= high)) * 100),
        "median_relative_interval_width_pct": float(np.median((high - low) / point) * 100),
        "gt_50pct_error_count": int(np.sum(errors > 0.50)),
        "gt_100pct_error_count": int(np.sum(errors > 1.00)),
    }


def format_table(results: dict) -> str:
    lines = [
        "| Split | Model | MdAPE % | Within ±10% | Within ±20% | Auto-Accept | Coverage | >50% err |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split, result in results.items():
        for name, metrics in result["models"].items():
            lines.append(
                f"| {split} | {name} | {metrics['mdape_pct']:.2f} | "
                f"{metrics['within_10_pct']:.2f}% | {metrics['within_20_pct']:.2f}% | "
                f"{metrics['auto_accept_pct']:.2f}% | {metrics['interval_coverage_pct']:.2f}% | "
                f"{metrics['gt_50pct_error_count']} |"
            )
    return "\n".join(lines)


def load_split(name: str):
    train = pd.read_csv(PROCESSED_DIR / f"train_{name}.csv", dtype={"row_id": str, "listing_id": str})
    test = pd.read_csv(PROCESSED_DIR / f"test_{name}.csv", dtype={"row_id": str, "listing_id": str})
    return train, test


def main():
    manifest_path = PROCESSED_DIR / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    results, bundle = {}, None
    for name in ("random", "locality_heldout"):
        train, test = load_split(name)
        lookup = build_locality_lookup(train)
        if name == "random":
            saved_lookup = pd.read_csv(PROCESSED_DIR / "localities_lookup.csv")
            lookup = saved_lookup
        X_train, X_test = build_features(train, lookup), build_features(test, lookup)
        y_train, y_test = train["price_lakhs"].to_numpy(), test["price_lakhs"].to_numpy()
        support = resolve_context(test, lookup)["locality_sample_count"].to_numpy()
        print(f"Training v2 {name}: {len(train):,} rows; testing {len(test):,} rows", flush=True)
        baseline_predictions = fit_baselines(train, test, X_train, X_test)
        models = train_lightgbm(X_train, y_train)
        point, raw_low, raw_high = [np.exp(models[key].predict(X_test)) for key in ("model_point", "model_low", "model_high")]
        low, high = ordered_interval(point, raw_low, raw_high)
        all_predictions = {**baseline_predictions, "LightGBM v2 + quantiles": (point, low, high)}
        metrics = {model_name: evaluate(y_test, *predictions, support) for model_name, predictions in all_predictions.items()}
        results[name] = {
            "train_rows": len(train), "test_rows": len(test),
            "train_localities": train["locality"].nunique(), "test_localities": test["locality"].nunique(),
            "locality_overlap_count": len(set(normalize_key(train["locality"])) & set(normalize_key(test["locality"]))),
            "known_locality_test_pct": float(np.mean(support > 0) * 100),
            "raw_quantile_crossing_pct": float(np.mean(raw_low > raw_high) * 100),
            "models": metrics,
        }
        if name == "random":
            scaler = StandardScaler().fit(X_train)
            nn = NearestNeighbors(n_neighbors=3, metric="euclidean", n_jobs=1).fit(scaler.transform(X_train))
            comparables = train[["row_id", "city", "locality", "sqft", "bhk", "floor", "age_years", "price_lakhs", "price_per_sqft"]].copy()
            comparables[["lat", "lon"]] = X_train[["lat", "lon"]].to_numpy()
            bundle = {
                "model_version": "ps1-v2-" + manifest["output_sha256"]["train_random.csv"][:12],
                "feature_cols": FEATURE_COLS, "target_transform": "log", **models,
                "scaler": scaler, "nn": nn, "comparables": comparables,
                "localities_lookup": lookup, "seed": SEED, "model_params": MODEL_PARAMS,
                "source_sha256": manifest["source_sha256"], "training_sha256": manifest["output_sha256"]["train_random.csv"],
                "versions": {package: version(package) for package in ("numpy", "pandas", "scikit-learn", "lightgbm", "shap", "joblib")},
                "python_version": platform.python_version(),
                "auto_accept_policy": {"max_relative_interval_width": AUTO_ACCEPT_MAX_RELATIVE_WIDTH,
                                       "min_locality_samples": AUTO_ACCEPT_MIN_LOCALITY_SAMPLES},
                "quantile_range": [QUANTILE_LOW, QUANTILE_HIGH],
            }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = MODEL_DIR / "valuation_bundle_v2.pkl"
    joblib.dump(bundle, bundle_path, compress=3)
    reloaded = joblib.load(bundle_path)
    random_test = pd.read_csv(PROCESSED_DIR / "test_random.csv")
    sample_row = random_test.loc[random_test["city"].eq("Gurgaon")].iloc[0]
    sample_input = sample_row[["city", "locality", "sqft", "bhk", "floor", "age_years"]].to_dict()
    sample_output = predict_valuation(sample_input, reloaded)
    table = format_table(results)
    print("\n" + table)
    print("\nSample v2 prediction:\n", json.dumps(sample_output, indent=2))


if __name__ == "__main__":
    main()

