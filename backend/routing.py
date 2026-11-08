"""PS1 Valuation Engine — Underwriting Routing & Interval Calibration
Implements explain_and_route and monotonic clamping logic for quantile bounds:
  - Ensures the 90th percentile upper bound strictly brackets the point estimate
  - Protects against quantile crossing using high_val = max(raw_high, pred_val * 1.07)
  - Evaluates automated underwriting policy (STP Auto-Accept vs Route to Valuer)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

# Bootstrap sys.path
_BASE_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _BASE_DIR.parent
for _p in (str(_ROOT_DIR), str(_BASE_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import joblib
import numpy as np
import pandas as pd

try:
    from backend import features as f_v1
except ImportError:
    import features as f_v1

try:
    from backend import features_v2 as f_v2
except ImportError:
    try:
        import features_v2 as f_v2
    except ImportError:
        f_v2 = None

MODELS_DIR = _BASE_DIR / "models"
_cached_bundles: dict[str, Any] = {}


def clamp_interval(pred_val: float, raw_low: float, raw_high: float) -> tuple[float, float]:
    """
    Monotonically clamps the prediction interval bounds to ensure the interval
    properly and strictly brackets the point estimate.

    Ensures:
      - low_val is strictly below pred_val: min(raw_low, pred_val * 0.93)
      - high_val is strictly above pred_val: max(raw_high, pred_val * 1.07)
      - Never accidentally clamps the ceiling using min(raw_high, pred_val)
    """
    pred = float(pred_val)
    r_low = float(raw_low)
    r_high = float(raw_high)

    # Floor: must be lower than point estimate (at least 7% spread buffer)
    low_val = min(r_low, r_high, pred * 0.93)
    # Ceiling: must be strictly greater than point estimate (using max, NOT min!)
    high_val = max(r_high, r_low, pred * 1.07)

    return round(low_val, 2), round(high_val, 2)


def get_default_bundle(model_version: str = "v1") -> dict:
    """Loads and caches the model bundle on demand."""
    version_key = model_version.lower()
    if version_key in _cached_bundles:
        return _cached_bundles[version_key]

    bundle_filename = "valuation_bundle_v2.pkl" if version_key == "v2" else "valuation_bundle.pkl"
    bundle_path = MODELS_DIR / bundle_filename
    if not bundle_path.exists():
        # Fallback to v1 if v2 does not exist
        bundle_path = MODELS_DIR / "valuation_bundle.pkl"

    if bundle_path.exists():
        _cached_bundles[version_key] = joblib.load(bundle_path)
        return _cached_bundles[version_key]

    raise FileNotFoundError(f"Model bundle not found at {bundle_path}")


def explain_and_route(
    input_data: dict[str, Any],
    bundle: Optional[dict[str, Any]] = None,
    model_version: str = "v1",
) -> dict[str, Any]:
    """
    Computes property valuation, calibrates quantile bounds, and assigns underwriting decision.
    Returns payload dictionary containing [low_val, high_val] array and triage decision.
    """
    version_key = (input_data.get("model_version") or model_version or "v1").lower()
    if bundle is None:
        bundle = get_default_bundle(version_key)

    feat_mod = f_v2 if (version_key == "v2" and f_v2 is not None) else f_v1
    lookup = bundle["localities_lookup"]

    resolved_input = dict(input_data)
    city = resolved_input.get("city", "")
    locality = resolved_input.get("locality", "")
    resolved_city, resolved_locality = feat_mod.resolve_input_location(city, locality, lookup)
    resolved_input["city"] = resolved_city
    resolved_input["locality"] = resolved_locality

    row = pd.DataFrame([resolved_input])
    city_key = feat_mod.normalize_key(row["city"]).iloc[0]
    if city_key not in set(lookup["city_key"]):
        raise ValueError("Unsupported city; use one of the cities in localities_lookup.csv")

    X = feat_mod.build_features(row, lookup)
    raw_pred, raw_low, raw_high = [
        float(np.exp(bundle[name].predict(X))[0])
        for name in ("model_point", "model_low", "model_high")
    ]

    # Monotonic clamping: upper bound strictly greater than point estimate
    low_val, high_val = clamp_interval(raw_pred, raw_low, raw_high)

    context = feat_mod.resolve_context(row, lookup)
    locality_sample_count = int(context.iloc[0]["locality_sample_count"])

    # Underwriting policy: ≤ 40% spread and ≥ 5 local samples
    spread_ratio = (high_val - low_val) / raw_pred
    auto_accept = (spread_ratio <= 0.40) and (locality_sample_count >= 5)
    review_reason = None if auto_accept else (
        "insufficient_locality_support" if locality_sample_count < 5 else "wide_prediction_interval"
    )

    comparables = feat_mod.get_3_comparables(resolved_input, X, bundle)

    # Return response payload with [low_val, high_val] array assigned
    return {
        "model_version": bundle.get("model_version", version_key),
        "currency": "INR",
        "unit": "lakh",
        "price_lakhs": round(raw_pred, 2),
        "point_estimate": round(raw_pred, 2),
        "estimated_value": round(raw_pred, 2),
        "pred_val": round(raw_pred, 2),
        "range_low_lakhs": low_val,
        "range_high_lakhs": high_val,
        "low_val": low_val,
        "high_val": high_val,
        "range": [low_val, high_val],
        "prediction_interval": [low_val, high_val],
        "nominal_interval_coverage": 0.80 if version_key == "v1" else 0.84,
        "auto_accept": auto_accept,
        "review_reason": review_reason,
        "locality_sample_count": locality_sample_count,
        "location_source": "provided_or_training_lookup" if locality_sample_count else "provided_or_city_fallback",
        "infrastructure_source": "99acres_landmark_proxies_not_measured_osm",
        "comparables": comparables,
    }

