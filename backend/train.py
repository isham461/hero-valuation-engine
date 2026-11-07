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

try:
    from .features import (
        AUTO_ACCEPT_MAX_RELATIVE_WIDTH, AUTO_ACCEPT_MIN_LOCALITY_SAMPLES, FEATURE_COLS,
        auto_accept_mask, build_features, build_locality_lookup, normalize_key,
        ordered_interval, predict_valuation, resolve_context, with_keys,
    )
except ImportError:
    from features import (
        AUTO_ACCEPT_MAX_RELATIVE_WIDTH, AUTO_ACCEPT_MIN_LOCALITY_SAMPLES, FEATURE_COLS,
        auto_accept_mask, build_features, build_locality_lookup, normalize_key,
        ordered_interval, predict_valuation, resolve_context, with_keys,
    )

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"
SEED = 42
MODEL_PARAMS = {
    "n_estimators": 600, "learning_rate": 0.04, "num_leaves": 31,
    "min_child_samples": 35, "reg_lambda": 2.0, "reg_alpha": 0.1,
    "subsample": 0.9, "subsample_freq": 1, "colsample_bytree": 1.0,
    "random_state": SEED, "n_jobs": 4, "verbosity": -1,
    "deterministic": True, "force_col_wise": True,
}


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
        q10, q90 = np.quantile(log_residuals, [0.1, 0.9])
        low, high = ordered_interval(point, point * np.exp(q10), point * np.exp(q90))
        result[name] = (point, low, high)
    return result


def train_lightgbm(X: pd.DataFrame, y: np.ndarray) -> dict:
    models = {}
    for name, objective, alpha in (
        ("model_point", "regression_l1", None),
        ("model_low", "quantile", 0.1),
        ("model_high", "quantile", 0.9),
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
    }


def format_table(results: dict) -> str:
    lines = [
        "| Split | Model | MdAPE % | Within ±10% | Within ±20% | Auto-Accept |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for split, result in results.items():
        for name, metrics in result["models"].items():
            lines.append(
                f"| {split} | {name} | {metrics['mdape_pct']:.2f} | "
                f"{metrics['within_10_pct']:.2f}% | {metrics['within_20_pct']:.2f}% | "
                f"{metrics['auto_accept_pct']:.2f}% |"
            )
    return "\n".join(lines)


def load_split(name: str):
    train = pd.read_csv(PROCESSED_DIR / f"train_{name}.csv", dtype={"row_id": str, "listing_id": str})
    test = pd.read_csv(PROCESSED_DIR / f"test_{name}.csv", dtype={"row_id": str, "listing_id": str})
    if set(train["row_id"]) & set(test["row_id"]):
        raise ValueError(f"Row leakage in {name}")
    overlap = set(normalize_key(train["locality"])) & set(normalize_key(test["locality"]))
    if name == "locality_heldout" and overlap:
        raise ValueError("Held-out test contains training localities")
    return train, test


def main():
    manifest_path = PROCESSED_DIR / "split_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("Run backend/prepare_data.py first")
    manifest = json.loads(manifest_path.read_text())
    for filename, expected in manifest["output_sha256"].items():
        actual = hashlib.sha256((PROCESSED_DIR / filename).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Locked benchmark file changed: {filename}")
    results, bundle = {}, None
    for name in ("random", "locality_heldout"):
        train, test = load_split(name)
        lookup = build_locality_lookup(train)
        if name == "random":
            saved_lookup = pd.read_csv(PROCESSED_DIR / "localities_lookup.csv")
            pd.testing.assert_frame_equal(lookup, saved_lookup, check_dtype=False, atol=1e-4, rtol=1e-7)
            lookup = saved_lookup
        X_train, X_test = build_features(train, lookup), build_features(test, lookup)
        y_train, y_test = train["price_lakhs"].to_numpy(), test["price_lakhs"].to_numpy()
        support = resolve_context(test, lookup)["locality_sample_count"].to_numpy()
        print(f"Training {name}: {len(train):,} rows; testing {len(test):,} rows", flush=True)
        baseline_predictions = fit_baselines(train, test, X_train, X_test)
        models = train_lightgbm(X_train, y_train)
        point, raw_low, raw_high = [np.exp(models[key].predict(X_test)) for key in ("model_point", "model_low", "model_high")]
        low, high = ordered_interval(point, raw_low, raw_high)
        all_predictions = {**baseline_predictions, "LightGBM + quantiles": (point, low, high)}
        metrics = {model_name: evaluate(y_test, *predictions, support) for model_name, predictions in all_predictions.items()}
        minimal_test = test[["city", "locality", "sqft", "bhk", "floor", "age_years"]]
        X_lookup_only = build_features(minimal_test, lookup)
        minimal_point, minimal_low, minimal_high = [np.exp(models[key].predict(X_lookup_only)) for key in ("model_point", "model_low", "model_high")]
        minimal_low, minimal_high = ordered_interval(minimal_point, minimal_low, minimal_high)
        results[name] = {
            "train_rows": len(train), "test_rows": len(test),
            "train_localities": train["locality"].nunique(), "test_localities": test["locality"].nunique(),
            "locality_overlap_count": len(set(normalize_key(train["locality"])) & set(normalize_key(test["locality"]))),
            "known_locality_test_pct": float(np.mean(support > 0) * 100),
            "raw_quantile_crossing_pct": float(np.mean(raw_low > raw_high) * 100),
            "models": metrics,
            "lightgbm_lookup_only_api_inputs": evaluate(y_test, minimal_point, minimal_low, minimal_high, support),
            "lightgbm_by_city": {
                city: evaluate(y_test[mask], point[mask], low[mask], high[mask], support[mask])
                for city in sorted(test["city"].unique())
                for mask in [test["city"].eq(city).to_numpy()]
            },
        }
        if name == "random":
            scaler = StandardScaler().fit(X_train)
            nn = NearestNeighbors(n_neighbors=3, metric="euclidean", n_jobs=1).fit(scaler.transform(X_train))
            comparables = train[["row_id", "city", "locality", "sqft", "bhk", "floor", "age_years", "price_lakhs", "price_per_sqft"]].copy()
            comparables[["lat", "lon"]] = X_train[["lat", "lon"]].to_numpy()
            bundle = {
                "model_version": "ps1-v1-" + manifest["output_sha256"]["train_random.csv"][:12],
                "feature_cols": FEATURE_COLS, "target_transform": "log", **models,
                "scaler": scaler, "nn": nn, "comparables": comparables,
                "localities_lookup": lookup, "seed": SEED, "model_params": MODEL_PARAMS,
                "source_sha256": manifest["source_sha256"], "training_sha256": manifest["output_sha256"]["train_random.csv"],
                "versions": {package: version(package) for package in ("numpy", "pandas", "scikit-learn", "lightgbm", "shap", "joblib")},
                "python_version": platform.python_version(),
                "auto_accept_policy": {"max_relative_interval_width": AUTO_ACCEPT_MAX_RELATIVE_WIDTH,
                                       "min_locality_samples": AUTO_ACCEPT_MIN_LOCALITY_SAMPLES},
            }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle_path = MODEL_DIR / "valuation_bundle.pkl"
    joblib.dump(bundle, bundle_path, compress=3)
    reloaded = joblib.load(bundle_path)
    random_test = pd.read_csv(PROCESSED_DIR / "test_random.csv")
    sample_row = random_test.loc[random_test["city"].eq("Gurgaon")].iloc[0] if random_test["city"].eq("Gurgaon").any() else random_test.iloc[0]
    sample_input = sample_row[["city", "locality", "sqft", "bhk", "floor", "age_years"]].to_dict()
    sample_output = predict_valuation(sample_input, reloaded)
    assert len(sample_output["comparables"]) == 3
    assert sample_output["range_low_lakhs"] <= sample_output["price_lakhs"] <= sample_output["range_high_lakhs"]
    import shap
    sample_features = build_features(pd.DataFrame([sample_input]), reloaded["localities_lookup"])
    explanation = shap.TreeExplainer(reloaded["model_point"])(sample_features)
    np.testing.assert_allclose(explanation.base_values + explanation.values.sum(axis=1), reloaded["model_point"].predict(sample_features), atol=1e-6)
    report = {
        "model_version": bundle["model_version"], "seed": SEED, "versions": bundle["versions"],
        "metric_definitions": {
            "mdape_pct": "100 * median(abs(actual - predicted) / actual)",
            "within_10_pct": "Percent of rows with absolute percentage error <= 10%",
            "within_20_pct": "Percent of rows with absolute percentage error <= 20%",
            "auto_accept_pct": "Percent with (high-low)/point <= 0.40 AND >=5 training listings in the exact city/locality; no actual test price is used",
            "intervals": "LightGBM log-price q10/q90, expanded to include point and correct crossing. Baselines use training-only 5-fold OOF log-residual q10/q90. Not guaranteed/calibrated coverage.",
        },
        "caveats": [
            "Listing asking prices from 2023, not transactions or current market valuations.",
            manifest["outlier_policy"], manifest["infrastructure_policy"],
            "Every model and baseline is retrained independently on each split's training rows.",
            "Primary benchmark uses available listing coordinates/proxies. Separate lookup-only metrics quantify the minimal API input path.",
            "GroupShuffleSplit holds out 20% of locality groups; the row fraction is approximate.",
            "Auto-accept is an illustrative uncertainty/support policy, not an underwriting approval.",
            "Repeated listing IDs and exact valuation tuples are deduplicated; unidentified near-duplicate listings may remain.",
        ],
        "splits": results, "shap_additivity_verified": True,
        "bundle_sha256": hashlib.sha256(bundle_path.read_bytes()).hexdigest(),
    }
    (PROCESSED_DIR / "evaluation_metrics.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    sample = {"input": sample_input, "prediction": sample_output}
    (PROCESSED_DIR / "sample_prediction.json").write_text(json.dumps(sample, indent=2, allow_nan=False) + "\n")
    table = format_table(results)
    terminal_output = table + "\n\nSample prediction JSON (minimal API input, reloaded bundle):\n" + json.dumps(sample, indent=2, allow_nan=False)
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    (BASE_DIR / "logs" / "training_summary.txt").write_text(terminal_output + "\n")
    print("\n" + terminal_output)
    print(f"\nSaved {bundle_path} ({bundle_path.stat().st_size / 1024 / 1024:.2f} MiB); SHAP additivity verified.")


if __name__ == "__main__":
    main()
