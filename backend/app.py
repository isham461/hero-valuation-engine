"""PS1 Valuation Engine — FastAPI Service (Person 3 Deliverables)
Implements the HTTP API contract defined in README.md:
  - POST /api/v1/valuate: Valuate a residential property with quantile range and 3 comparables
  - GET  /api/v1/cities: List all supported cities and macro-regions for UI dropdowns
  - GET  /api/v1/localities: List localities for a selected city (with optional search filter)
  - GET  /health: Service readiness and model metadata
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend import features as f_v1
try:
    from backend import features_v2 as f_v2
except ImportError:
    f_v2 = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ps1-engine")

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data" / "processed"

# In-memory bundle store loaded at startup
bundles: dict[str, Any] = {}
lookup_cache: dict[str, Any] = {
    "cities": [],
    "localities_by_city": {},
    "all_localities": [],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model bundles and lookup tables once at startup."""
    v1_path = MODELS_DIR / "valuation_bundle.pkl"
    if v1_path.exists():
        bundles["v1"] = joblib.load(v1_path)
        logger.info("Loaded Model Bundle v1: %s", bundles["v1"].get("model_version"))
    else:
        logger.warning("Model Bundle v1 not found at %s", v1_path)

    v2_path = MODELS_DIR / "valuation_bundle_v2.pkl"
    if v2_path.exists():
        bundles["v2"] = joblib.load(v2_path)
        logger.info("Loaded Model Bundle v2: %s", bundles["v2"].get("model_version"))

    lookup_path = DATA_DIR / "localities_lookup.csv"
    if lookup_path.exists():
        df = pd.read_csv(lookup_path)
        cities = sorted(df["city"].unique().tolist())
        # Add macro-city aliases for UI convenience
        macro_cities = ["Mumbai", "Kolkata", "Gurgaon", "Hyderabad"]
        for mc in macro_cities:
            if mc not in cities:
                cities.append(mc)
        lookup_cache["cities"] = sorted(cities)

        by_city: dict[str, list[str]] = {}
        for city, group in df.groupby("city"):
            by_city[city] = sorted(group["locality"].dropna().unique().tolist())
        # Aggregate macro cities
        by_city["Mumbai"] = sorted(df[df["city"].str.contains("Mumbai|Thane|Mira Road", case=False)]["locality"].dropna().unique().tolist())
        by_city["Kolkata"] = sorted(df[df["city"].str.contains("Kolkata", case=False)]["locality"].dropna().unique().tolist())
        lookup_cache["localities_by_city"] = by_city
        lookup_cache["all_localities"] = sorted(df["locality"].dropna().unique().tolist())
        logger.info("Initialized localities lookup: %d localities across %d cities", len(df), len(by_city))
    else:
        logger.warning("Localities lookup not found at %s", lookup_path)

    yield
    bundles.clear()
    lookup_cache.clear()


app = FastAPI(
    title="PS1 Valuation Engine API",
    description="Automated Residential Property Valuation Engine for Hero Housing Fintech Challenge (Problem Statement 1)",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integration (Vite dev server runs on 5173 by default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request & Response Schemas
# ============================================================================

class ValuationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str = Field(..., min_length=2, max_length=100, description="City name (e.g. 'Gurgaon', 'Mumbai', 'Hyderabad')")
    locality: str = Field(..., min_length=2, max_length=120, description="Locality or Sector name (e.g. 'Sector 63', 'Andheri West')")
    sqft: float = Field(..., ge=300.0, le=10000.0, description="Super Built-up / Built-up area in square feet (300 to 10,000)")
    bhk: int = Field(..., ge=1, le=10, description="Number of bedrooms (1 to 10)")
    floor: Optional[float] = Field(default=None, ge=-5.0, le=150.0, description="Floor number (-1 for basement, 0 for ground; defaults to training median)")
    age_years: Optional[float] = Field(default=None, ge=0.0, le=120.0, description="Property age in years (0 for new/under-construction; defaults to training median)")
    lat: Optional[float] = Field(default=None, ge=8.0, le=35.0, description="Optional latitude coordinate (Indian bounds: 8.0 to 35.0)")
    lon: Optional[float] = Field(default=None, ge=68.0, le=97.0, description="Optional longitude coordinate (Indian bounds: 68.0 to 97.0)")
    model_version: Optional[str] = Field(default="v1", description="Model version to use ('v1' for locked benchmark, 'v2' for improved 9.96% model)")

    @field_validator("city", "locality")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Must not be empty or whitespace only")
        return cleaned


class ComparableListing(BaseModel):
    row_id: str
    city: str
    locality: str
    sqft: float
    bhk: int
    floor: float
    age_years: float
    lat: float
    lon: float
    price_lakhs: float
    price_per_sqft: float
    distance_km: float
    feature_distance: float


class ValuationResponse(BaseModel):
    model_version: str
    currency: str = "INR"
    unit: str = "lakh"
    price_lakhs: float
    range_low_lakhs: float
    range_high_lakhs: float
    nominal_interval_coverage: float
    auto_accept: bool
    review_reason: Optional[str]
    locality_sample_count: int
    location_source: str
    infrastructure_source: str
    comparables: list[ComparableListing]


# ============================================================================
# API Routes
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    return {
        "service": "PS1 Valuation Engine API",
        "challenge": "Hero Housing Fintech Challenge (Problem Statement 1)",
        "status": "online",
        "documentation": "/docs",
        "available_models": list(bundles.keys()),
    }


@app.get("/health", tags=["System"])
async def health_check():
    loaded_models = list(bundles.keys())
    if not loaded_models:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model bundles not loaded",
        )
    return {
        "status": "healthy",
        "models_loaded": loaded_models,
        "available_cities_count": len(lookup_cache.get("cities", [])),
        "available_localities_count": len(lookup_cache.get("all_localities", [])),
    }


@app.get("/api/v1/cities", tags=["Metadata"])
async def list_cities():
    """Returns all supported cities and metro groups for frontend dropdowns."""
    cities = lookup_cache.get("cities", [])
    if not cities:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cities lookup not initialized",
        )
    return {"cities": cities}


@app.get("/api/v1/localities", tags=["Metadata"])
async def list_localities(
    city: Optional[str] = Query(None, description="Filter localities by city name"),
    q: Optional[str] = Query(None, description="Optional search substring to autocomplete"),
):
    """Returns localities for a given city with optional autocomplete search."""
    by_city = lookup_cache.get("localities_by_city", {})
    if city:
        # Match city case-insensitively
        matched_localities = []
        for c, locs in by_city.items():
            if c.lower() == city.lower() or city.lower() in c.lower():
                matched_localities.extend(locs)
        localities = sorted(list(set(matched_localities)))
    else:
        localities = lookup_cache.get("all_localities", [])

    if q:
        query_str = q.strip().lower()
        localities = [loc for loc in localities if query_str in loc.lower()]

    return {"city": city, "total": len(localities), "localities": localities[:100]}


@app.post("/api/v1/valuate", response_model=ValuationResponse, tags=["Valuation"])
async def valuate_property(request: ValuationRequest):
    """Predicts property valuation in Indian Lakhs with confidence intervals and 3 comparables."""
    version_key = (request.model_version or "v1").lower()
    if version_key not in bundles:
        # Fallback to v1 if requested version not loaded
        version_key = "v1" if "v1" in bundles else list(bundles.keys())[0] if bundles else None

    if not version_key or version_key not in bundles:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model bundle is unavailable. Ensure train.py has run.",
        )

    bundle = bundles[version_key]
    engine_module = f_v2 if (version_key == "v2" and f_v2 is not None) else f_v1

    # Convert request to input dictionary
    input_dict: dict[str, Any] = {
        "city": request.city,
        "locality": request.locality,
        "sqft": request.sqft,
        "bhk": request.bhk,
    }
    if request.floor is not None:
        input_dict["floor"] = request.floor
    if request.age_years is not None:
        input_dict["age_years"] = request.age_years
    if request.lat is not None:
        input_dict["lat"] = request.lat
    if request.lon is not None:
        input_dict["lon"] = request.lon

    try:
        result = engine_module.predict_valuation(input_dict, bundle)
        return result
    except ValueError as e:
        logger.warning("Valuation validation error: %s", e)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        logger.error("Valuation engine failure: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Valuation calculation failed")

