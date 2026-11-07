from __future__ import annotations

import re
import numpy as np
import pandas as pd

FEATURE_COLS = [
    "sqft", "bhk", "floor", "age_years", "lat", "lon",
    "osm_schools_2km", "osm_hospitals_2km", "osm_metro_dist_km",
    "sqft_per_bhk", "is_high_floor", "amenity_index",
]
CONTEXT_COLS = [
    "lat", "lon", "osm_schools_2km", "osm_hospitals_2km",
    "osm_metro_dist_km", "floor", "age_years",
]
EARTH_RADIUS_KM = 6371.0088
AUTO_ACCEPT_MAX_RELATIVE_WIDTH = 0.40
AUTO_ACCEPT_MIN_LOCALITY_SAMPLES = 5

CITY_ALIASES: dict[str, list[str]] = {
    "mumbai": [
        "mumbai andheri-dahisar", "central mumbai suburbs", "mumbai harbour",
        "south mumbai", "mumbai south west", "mumbai beyond thane",
        "navi mumbai", "thane", "mira road and beyond",
    ],
    "bombay": [
        "mumbai andheri-dahisar", "central mumbai suburbs", "mumbai harbour",
        "south mumbai", "mumbai south west", "mumbai beyond thane",
        "navi mumbai", "thane", "mira road and beyond",
    ],
    "kolkata": [
        "kolkata south", "kolkata north", "kolkata east",
        "kolkata central", "kolkata west",
    ],
    "calcutta": [
        "kolkata south", "kolkata north", "kolkata east",
        "kolkata central", "kolkata west",
    ],
    "gurugram": ["gurgaon"],
    "delhi ncr": ["gurgaon"],
    "delhi": ["gurgaon"],
    "secunderabad": ["secunderabad", "hyderabad"],
    "hyderabad": ["hyderabad", "secunderabad"],
}


def clean_key(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9\s]", " ", str(text).lower()).strip()


def resolve_input_location(city: str, locality: str, lookup_df: pd.DataFrame) -> tuple[str, str]:
    city_str = str(city).strip() if city is not None else ""
    loc_str = str(locality).strip() if locality is not None else ""
    if not city_str:
        return city_str, loc_str

    ck = normalize_key(pd.Series([city_str])).iloc[0]
    lk = normalize_key(pd.Series([loc_str])).iloc[0]

    exact = lookup_df[(lookup_df["city_key"] == ck) & (lookup_df["locality_key"] == lk)]
    if not exact.empty:
        return exact.iloc[0]["city"], exact.iloc[0]["locality"]

    candidate_cities = CITY_ALIASES.get(ck, [ck] if ck in set(lookup_df["city_key"]) else [])
    if not candidate_cities:
        matched = [c for c in lookup_df["city_key"].unique() if ck in c or c in ck]
        candidate_cities = matched if matched else []

    if not candidate_cities:
        return city_str, loc_str

    subset = lookup_df[lookup_df["city_key"].isin(candidate_cities)]
    if subset.empty:
        return city_str, loc_str

    lk_clean = clean_key(loc_str)
    for _, row in subset.iterrows():
        if lk_clean == clean_key(row["locality_key"]):
            return row["city"], row["locality"]

    lk_words = set(lk_clean.split())
    if lk_words:
        best_match = None
        best_score = 0.0
        for _, row in subset.iterrows():
            row_words = set(clean_key(row["locality_key"]).split())
            if not row_words:
                continue
            intersection = lk_words & row_words
            score = len(intersection) / max(len(lk_words), len(row_words))
            if score > best_score and score >= 0.6:
                best_score = score
                best_match = (row["city"], row["locality"])
        if best_match:
            return best_match

    if ck in CITY_ALIASES or candidate_cities != [ck]:
        return subset.iloc[0]["city"], loc_str

    return city_str, loc_str


def normalize_key(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip().str.lower()


def with_keys(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in ("city", "locality"):
        if column not in result:
            raise ValueError(f"Missing required column: {column}")
        result[f"{column}_key"] = normalize_key(result[column])
    return result


def build_locality_lookup(train: pd.DataFrame) -> pd.DataFrame:
    keyed = with_keys(train)
    aggregations = {column: (column, "median") for column in CONTEXT_COLS}
    return keyed.groupby(["city_key", "locality_key"], sort=True).agg(
        city=("city", "first"), locality=("locality", "first"),
        **aggregations,
        locality_sample_count=("price_per_sqft", "size"),
        locality_median_ppsqft=("price_per_sqft", "median"),
    ).reset_index()


def resolve_context(df: pd.DataFrame, localities_df: pd.DataFrame) -> pd.DataFrame:
    if localities_df.empty:
        raise ValueError("The training locality lookup must not be empty")
    result = with_keys(df).reset_index(drop=True)
    lookup = with_keys(localities_df)
    if lookup.duplicated(["city_key", "locality_key"]).any():
        raise ValueError("Locality lookup keys must be unique")
    columns = [column for column in CONTEXT_COLS if column in lookup]
    merged = result[["city_key", "locality_key"]].merge(
        lookup[["city_key", "locality_key", *columns, "locality_sample_count"]],
        on=["city_key", "locality_key"], how="left", validate="many_to_one", sort=False,
    )
    lat = pd.to_numeric(result.get("lat", pd.Series(np.nan, index=result.index)), errors="coerce")
    lon = pd.to_numeric(result.get("lon", pd.Series(np.nan, index=result.index)), errors="coerce")
    swap = lat.between(68, 97) & lon.between(8, 35)
    lat, lon = lat.where(~swap, lon), lon.where(~swap, lat)
    valid = lat.between(8, 35) & lon.between(68, 97)
    result["lat"], result["lon"] = lat.where(valid), lon.where(valid)
    city_medians = lookup.groupby("city_key")[columns].median()
    for column in columns:
        values = pd.to_numeric(result.get(column, pd.Series(np.nan, index=result.index)), errors="coerce")
        result[column] = (
            values.replace([np.inf, -np.inf], np.nan)
            .fillna(merged[column])
            .fillna(result["city_key"].map(city_medians[column]))
            .fillna(lookup[column].median())
        )
    result["locality_sample_count"] = merged["locality_sample_count"].fillna(0).astype(int)
    return result


def build_features(df: pd.DataFrame, localities_df: pd.DataFrame) -> pd.DataFrame:
    result = resolve_context(df, localities_df)
    for column in FEATURE_COLS[:9]:
        if column not in result:
            raise ValueError(f"Missing required feature: {column}")
        result[column] = pd.to_numeric(result[column], errors="coerce")
    if not result["sqft"].between(300, 10000).all():
        raise ValueError("sqft must be between 300 and 10000")
    if not result["bhk"].between(1, 10).all():
        raise ValueError("bhk must be between 1 and 10")
    if not result["floor"].between(-5, 150).all() or not result["age_years"].between(0, 120).all():
        raise ValueError("floor or age_years is outside the supported range")
    if not result["lat"].between(8, 35).all() or not result["lon"].between(68, 97).all():
        raise ValueError("Valid Indian coordinates or training coordinate fallbacks are required")
    infrastructure = result[["osm_schools_2km", "osm_hospitals_2km", "osm_metro_dist_km"]]
    if not infrastructure.ge(0).all().all():
        raise ValueError("Infrastructure proxies must be nonnegative")
    result["sqft_per_bhk"] = result["sqft"] / result["bhk"]
    result["is_high_floor"] = (result["floor"] >= 10).astype(float)
    result["amenity_index"] = (
        result["osm_schools_2km"] + 1.5 * result["osm_hospitals_2km"]
        + 2.0 / (1.0 + result["osm_metro_dist_km"])
    )
    features = result[FEATURE_COLS].astype(float)
    if not np.isfinite(features.to_numpy()).all():
        raise ValueError("Features contain missing or non-finite values")
    features.index = df.index
    return features


def haversine_km(lat: float, lon: float, other_lat, other_lon) -> np.ndarray:
    lat1, lon1 = np.radians([lat, lon])
    lat2, lon2 = np.radians(np.asarray(other_lat)), np.radians(np.asarray(other_lon))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def get_3_comparables(input_row_dict: dict, X_row_df: pd.DataFrame, bundle: dict) -> list[dict]:
    if len(X_row_df) != 1 or list(X_row_df.columns) != FEATURE_COLS:
        raise ValueError("Comparables require one row in FEATURE_COLS order")
    candidates = bundle["comparables"].reset_index(drop=True)
    city_key = normalize_key(pd.Series([input_row_dict["city"]])).iloc[0]
    eligible = normalize_key(candidates["city"]).eq(city_key)
    if input_row_dict.get("row_id"):
        eligible &= candidates["row_id"].ne(input_row_dict["row_id"])
    if not eligible.any():
        return []
    scaled = bundle["scaler"].transform(X_row_df)
    count = min(100, len(candidates))
    distances, indices = bundle["nn"].kneighbors(scaled, n_neighbors=count)
    mask = eligible.iloc[indices[0]].to_numpy()
    if mask.sum() < min(3, int(eligible.sum())) and count < len(candidates):
        distances, indices = bundle["nn"].kneighbors(scaled, n_neighbors=len(candidates))
        mask = eligible.iloc[indices[0]].to_numpy()
    selected = candidates.iloc[indices[0][mask]].copy()
    selected["feature_distance"] = distances[0][mask]
    selected["distance_km"] = haversine_km(
        float(X_row_df.iloc[0]["lat"]), float(X_row_df.iloc[0]["lon"]),
        selected["lat"], selected["lon"],
    )
    selected["score"] = selected["feature_distance"] + np.minimum(selected["distance_km"] / 5, 20)
    selected = selected.sort_values(["score", "row_id"]).head(3)
    records = []
    for _, row in selected.iterrows():
        records.append({
            "row_id": row["row_id"], "city": row["city"], "locality": row["locality"],
            "sqft": round(float(row["sqft"]), 2), "bhk": int(row["bhk"]),
            "floor": float(row["floor"]), "age_years": float(row["age_years"]),
            "lat": float(row["lat"]), "lon": float(row["lon"]),
            "price_lakhs": round(float(row["price_lakhs"]), 2),
            "price_per_sqft": round(float(row["price_per_sqft"]), 2),
            "distance_km": round(float(row["distance_km"]), 3),
            "feature_distance": round(float(row["feature_distance"]), 3),
        })
    return records


def ordered_interval(point, low, high):
    return np.minimum(np.minimum(low, high), point), np.maximum(np.maximum(low, high), point)


def auto_accept_mask(point, low, high, locality_sample_count):
    return (
        ((np.asarray(high) - np.asarray(low)) / np.asarray(point) <= AUTO_ACCEPT_MAX_RELATIVE_WIDTH)
        & (np.asarray(locality_sample_count) >= AUTO_ACCEPT_MIN_LOCALITY_SAMPLES)
    )


def predict_valuation(input_row_dict: dict, bundle: dict) -> dict:
    lookup = bundle["localities_lookup"]
    resolved_input = dict(input_row_dict)
    city = resolved_input.get("city", "")
    locality = resolved_input.get("locality", "")
    resolved_city, resolved_locality = resolve_input_location(city, locality, lookup)
    resolved_input["city"] = resolved_city
    resolved_input["locality"] = resolved_locality

    row = pd.DataFrame([resolved_input])
    city_key = normalize_key(row["city"]).iloc[0]
    if city_key not in set(lookup["city_key"]):
        raise ValueError("Unsupported city; use one of the cities in localities_lookup.csv")
    X = build_features(row, lookup)
    point, raw_low, raw_high = [
        np.exp(bundle[name].predict(X)) for name in ("model_point", "model_low", "model_high")
    ]
    low, high = ordered_interval(point, raw_low, raw_high)
    context = resolve_context(row, lookup)
    sample_count = int(context.iloc[0]["locality_sample_count"])
    accepted = bool(auto_accept_mask(point, low, high, [sample_count])[0])
    return {
        "model_version": bundle["model_version"], "currency": "INR", "unit": "lakh",
        "price_lakhs": round(float(point[0]), 2),
        "range_low_lakhs": round(float(low[0]), 2), "range_high_lakhs": round(float(high[0]), 2),
        "nominal_interval_coverage": 0.8, "auto_accept": accepted,
        "review_reason": None if accepted else (
            "insufficient_locality_support" if sample_count < AUTO_ACCEPT_MIN_LOCALITY_SAMPLES else "wide_prediction_interval"
        ),
        "locality_sample_count": sample_count,
        "location_source": "provided_or_training_lookup" if sample_count else "provided_or_city_fallback",
        "infrastructure_source": "99acres_landmark_proxies_not_measured_osm",
        "comparables": get_3_comparables(resolved_input, X, bundle),
    }
