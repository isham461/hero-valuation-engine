"""PS1 Valuation Engine — Model Explainability Engine (Member 1 Deliverable)
Provides tree-based SHAP local and global feature attribution:
  - Local property waterfall explanation: converts log-space SHAP values into rupee (Lakh) impacts
  - Formatted driver contributions ready for Member 2's React chart components
  - Global feature importance analysis across test benchmarks
"""
from __future__ import annotations

import logging
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
import shap

try:
    from backend import features as f_v1
    from backend import features_v2 as f_v2
except ImportError:
    import features as f_v1
    try:
        import features_v2 as f_v2
    except ImportError:
        f_v2 = None

logger = logging.getLogger("ps1-explain")

FRIENDLY_NAMES = {
    "sqft": "Built-up Area (Sqft)",
    "log_sqft": "Log Area Scale",
    "bhk": "Bedroom Count (BHK)",
    "sqft_per_bhk": "Room Spaciousness (Sqft/BHK)",
    "log_sqft_per_bhk": "Room Spaciousness Scale",
    "floor": "Floor Level",
    "is_high_floor": "High Floor Flag",
    "age_years": "Property Age",
    "lat": "Geographic Latitude",
    "lon": "Geographic Longitude",
    "osm_schools_2km": "Nearby Schools (2km proxy)",
    "osm_hospitals_2km": "Nearby Hospitals (2km proxy)",
    "osm_metro_dist_km": "Metro Distance Proxy",
    "amenity_index": "Local Infrastructure Index",
    "locality_median_ppsqft": "Locality Historical Price Rate",
}


class PropertyExplainer:
    """Explains LightGBM valuation models using SHAP TreeExplainer."""

    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle
        self.model = bundle["model_point"]
        self.feature_cols = bundle["feature_cols"]
        self.lookup = bundle["localities_lookup"]
        self.explainer = shap.TreeExplainer(self.model)
        self.is_v2 = "log_sqft" in self.feature_cols
        self.features_module = f_v2 if (self.is_v2 and f_v2 is not None) else f_v1

    def explain_property(self, input_dict: dict[str, Any]) -> dict[str, Any]:
        """Calculates exact SHAP contributions and converts log impacts to Lakh rupee adjustments."""
        # Resolve location aliases if present
        resolved_input = dict(input_dict)
        if hasattr(self.features_module, "resolve_input_location"):
            rc, rl = self.features_module.resolve_input_location(
                resolved_input.get("city", ""),
                resolved_input.get("locality", ""),
                self.lookup,
            )
            resolved_input["city"] = rc
            resolved_input["locality"] = rl

        row = pd.DataFrame([resolved_input])
        X = self.features_module.build_features(row, self.lookup)

        # Compute SHAP explanation on log price
        shap_values = self.explainer(X)
        base_log = float(shap_values.base_values[0])
        pred_log = float(self.model.predict(X)[0])
        contributions_log = shap_values.values[0]

        # Verify additivity: base + sum(contributions) == prediction
        assert np.isclose(base_log + contributions_log.sum(), pred_log, atol=1e-5), "SHAP additivity failed"

        base_lakhs = float(np.exp(base_log))
        pred_lakhs = float(np.exp(pred_log))

        # Convert log differences to proportional rupee (Lakh) impacts
        total_log_diff = pred_log - base_log
        rupee_diff = pred_lakhs - base_lakhs

        drivers = []
        for feat_name, log_val, raw_val in zip(self.feature_cols, contributions_log, X.iloc[0]):
            # Proportional rupee impact based on exponential scaling
            pct_impact = float((np.exp(log_val) - 1.0) * 100.0)
            if abs(total_log_diff) > 1e-6:
                impact_lakhs = float(rupee_diff * (log_val / total_log_diff))
            else:
                impact_lakhs = 0.0

            drivers.append({
                "feature": feat_name,
                "display_name": FRIENDLY_NAMES.get(feat_name, feat_name),
                "feature_value": round(float(raw_val), 4),
                "log_shap": round(float(log_val), 4),
                "impact_lakhs": round(impact_lakhs, 2),
                "impact_pct": round(pct_impact, 2),
                "is_positive": impact_lakhs >= 0,
            })

        # Sort drivers by absolute rupee impact
        drivers.sort(key=lambda d: abs(d["impact_lakhs"]), reverse=True)

        top_positive = [d for d in drivers if d["impact_lakhs"] > 0][:3]
        top_negative = [d for d in drivers if d["impact_lakhs"] < 0][:3]

        # Generate human-readable narrative explanation
        pos_summaries = [f"{d['display_name']} (+₹{d['impact_lakhs']:.1f}L)" for d in top_positive]
        neg_summaries = [f"{d['display_name']} (-₹{abs(d['impact_lakhs']):.1f}L)" for d in top_negative]

        narrative_parts = []
        if pos_summaries:
            narrative_parts.append(f"Primary value premiums come from {', '.join(pos_summaries)}.")
        if neg_summaries:
            narrative_parts.append(f"Value reductions are driven by {', '.join(neg_summaries)}.")
        narrative = " ".join(narrative_parts) if narrative_parts else "Property valuation aligns closely with market baseline."

        return {
            "model_version": self.bundle.get("model_version", "ps1"),
            "base_market_lakhs": round(base_lakhs, 2),
            "predicted_price_lakhs": round(pred_lakhs, 2),
            "total_adjustment_lakhs": round(rupee_diff, 2),
            "narrative_summary": narrative,
            "drivers": drivers,
            "top_positive_drivers": top_positive,
            "top_negative_drivers": top_negative,
        }


def explain_single_property(input_dict: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    explainer = PropertyExplainer(bundle)
    return explainer.explain_property(input_dict)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    bundle_path = base_dir / "models" / "valuation_bundle.pkl"
    if bundle_path.exists():
        bundle = joblib.load(bundle_path)
        sample = {
            "city": "Gurgaon", "locality": "Sector 63",
            "sqft": 3794, "bhk": 5, "floor": 2, "age_years": 0.5,
        }
        res = explain_single_property(sample, bundle)
        print("Market Base: ₹", res["base_market_lakhs"], "Lakhs")
        print("Predicted:   ₹", res["predicted_price_lakhs"], "Lakhs")
        print("Narrative:  ", res["narrative_summary"])
        print("\nTop Drivers:")
        for d in res["drivers"][:5]:
            print(f"  • {d['display_name']:<30}: {d['impact_lakhs']:+6.2f} Lakhs ({d['impact_pct']:+5.1f}%)")
