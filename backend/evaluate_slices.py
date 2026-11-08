"""PS1 Valuation Engine — Slice & Submarket Evaluation (Person 2 Deliverables)
Performs fine-grained underwriting analysis across property slices:
  - By Major City / Metro Region
  - By Price Tier (<50L, 50-100L, 100-200L, 200-500L, 500L+)
  - By Bedroom Count (1 BHK through 5+ BHK)
  - By Locality Support Tier (Unseen, Low 1-4, Adequate 5-20, High 20+)
  - By Property Age (New <2y, Mid 2-10y, Mature >10y)
Outputs structured slice metrics to backend/logs/slice_performance_report.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Bootstrap sys.path
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = Path(__file__).resolve().parent
for _p in (str(_ROOT), str(_BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import joblib
import numpy as np
import pandas as pd

try:
    from backend import features as f_v1
    from backend import features_v2 as f_v2
except ImportError:
    import features as f_v1
    try:
        import features_v2 as f_v2
    except ImportError:
        f_v2 = None

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"


def compute_slice_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_low: np.ndarray, y_high: np.ndarray, support: np.ndarray) -> dict[str, Any]:
    n = len(y_true)
    if n == 0:
        return {"n": 0}

    errors = np.abs(y_true - y_pred) / y_true
    pct_errors = (y_pred - y_true) / y_true  # signed bias
    relative_widths = (y_high - y_low) / y_pred
    accepted = (relative_widths <= 0.40) & (support >= 5)
    in_interval = (y_true >= y_low) & (y_true <= y_high)

    return {
        "n_samples": int(n),
        "mdape_pct": round(float(np.median(errors) * 100), 2),
        "within_10_pct": round(float(np.mean(errors <= 0.10) * 100), 2),
        "within_20_pct": round(float(np.mean(errors <= 0.20) * 100), 2),
        "median_bias_pct": round(float(np.median(pct_errors) * 100), 2),
        "interval_coverage_pct": round(float(np.mean(in_interval) * 100), 2),
        "auto_accept_pct": round(float(np.mean(accepted) * 100), 2),
        "auto_accept_count": int(np.sum(accepted)),
        "accepted_within_20_pct": round(float(np.mean(errors[accepted] <= 0.20) * 100), 2) if np.any(accepted) else None,
        "gt_50pct_error_count": int(np.sum(errors > 0.50)),
    }


def run_slice_evaluation(bundle_path: Path, split_name: str = "random"):
    bundle = joblib.load(bundle_path)
    test_df = pd.read_csv(PROCESSED_DIR / f"test_{split_name}.csv")
    lookup = bundle["localities_lookup"]
    feature_cols = bundle["feature_cols"]

    is_v2 = "log_sqft" in feature_cols
    feat_mod = f_v2 if (is_v2 and f_v2 is not None) else f_v1

    X_test = feat_mod.build_features(test_df, lookup)
    y_test = test_df["price_lakhs"].to_numpy()

    p_point = np.exp(bundle["model_point"].predict(X_test))
    p_low = np.exp(bundle["model_low"].predict(X_test))
    p_high = np.exp(bundle["model_high"].predict(X_test))
    low, high = feat_mod.ordered_interval(p_point, p_low, p_high)

    context = feat_mod.resolve_context(test_df, lookup)
    support = context["locality_sample_count"].to_numpy()

    df = test_df.copy()
    df["y_true"] = y_test
    df["y_pred"] = p_point
    df["y_low"] = low
    df["y_high"] = high
    df["support"] = support

    # Define slices
    df["price_tier"] = pd.cut(
        df["price_lakhs"],
        bins=[0, 50, 100, 200, 500, 10000],
        labels=["< 50L (Budget)", "50L - 1Cr (Affordable)", "1Cr - 2Cr (Mid-Market)", "2Cr - 5Cr (Premium)", "5Cr+ (Luxury)"],
    )

    df["bhk_tier"] = df["bhk"].apply(lambda b: f"{int(b)} BHK" if b <= 4 else "5+ BHK (Large/Villa)")

    df["support_tier"] = pd.cut(
        df["support"],
        bins=[-1, 0, 4, 20, 10000],
        labels=["Unseen Locality (0 samples)", "Low Support (1-4 samples)", "Adequate Support (5-20 samples)", "High Support (20+ samples)"],
    )

    df["age_tier"] = pd.cut(
        df["age_years"],
        bins=[-1, 2, 10, 200],
        labels=["New / UC (< 2 yrs)", "Modern (2 - 10 yrs)", "Mature (> 10 yrs)"],
    )

    report = {
        "model_version": bundle.get("model_version"),
        "split_evaluated": split_name,
        "overall": compute_slice_metrics(y_test, p_point, low, high, support),
        "by_price_tier": {},
        "by_bhk": {},
        "by_city": {},
        "by_support_tier": {},
        "by_age_tier": {},
    }

    for col, key in [
        ("price_tier", "by_price_tier"),
        ("bhk_tier", "by_bhk"),
        ("city", "by_city"),
        ("support_tier", "by_support_tier"),
        ("age_tier", "by_age_tier"),
    ]:
        for val, group in df.groupby(col, observed=False):
            report[key][str(val)] = compute_slice_metrics(
                group["y_true"].to_numpy(),
                group["y_pred"].to_numpy(),
                group["y_low"].to_numpy(),
                group["y_high"].to_numpy(),
                group["support"].to_numpy(),
            )

    out_file = LOGS_DIR / f"slice_performance_{split_name}_{'v2' if is_v2 else 'v1'}.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(f"Saved slice evaluation report to {out_file}")
    return report


if __name__ == "__main__":
    v1_bundle = MODELS_DIR / "valuation_bundle.pkl"
    v2_bundle = MODELS_DIR / "valuation_bundle_v2.pkl"

    if v1_bundle.exists():
        print("Running slice evaluation for v1...")
        run_slice_evaluation(v1_bundle, "random")

    if v2_bundle.exists():
        print("Running slice evaluation for v2...")
        run_slice_evaluation(v2_bundle, "random")
