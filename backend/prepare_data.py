from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, train_test_split

try:
    from .features import CONTEXT_COLS, build_locality_lookup, normalize_key, resolve_context
except ImportError:
    from features import CONTEXT_COLS, build_locality_lookup, normalize_key, resolve_context

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
SEED = 42
AGE_CODES = {"1": 3.0, "2": 7.5, "3": 15.0, "5": 0.0, "6": 0.5}
RESIDENTIAL_TYPES = {
    "residential apartment", "independent house/villa", "independent/builder floor",
    "farm house", "serviced apartments", "studio apartment",
    "001", "002", "004", "005", "022", "090",
}
EMPTY_STRINGS = {"", "nan", "none", "null", "n/a", "na", "on request", "price on request"}
DEDUP_COLS = ["city", "locality", "sqft", "bhk", "floor", "price_lakhs"]


def clean_string(value) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    return "" if text.lower() in EMPTY_STRINGS else text


def parse_structured(value):
    if isinstance(value, (dict, list)):
        return value
    text = clean_string(value)
    if not text or len(text) > 100_000:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        try:
            return ast.literal_eval(text)
        except (ValueError, SyntaxError, TypeError, RecursionError):
            return None


def parse_price(value, numeric_rupees: bool = False) -> float:
    text = clean_string(value).lower().replace(",", "")
    if not text or re.search(r"/|per\s+(sq|month|bed)", text):
        return np.nan
    parts = re.findall(r"(\d+(?:\.\d+)?)\s*(crores?|cr\b|lakhs?|lacs?|lac\b|l\b)?", text)
    if not parts or re.search(r"^[^\d-]*-\s*\d", text):
        return np.nan
    last_unit = next((unit for _, unit in reversed(parts) if unit), "")
    values = []
    for number, unit in parts:
        value = float(number)
        unit = unit or last_unit
        if unit.startswith("cr"):
            value *= 100
        elif unit.startswith("l"):
            pass
        elif numeric_rupees or value >= 10_000 or re.search(r"₹|\brs\b|\binr\b|rupees?", text):
            value /= 100_000
        values.append(value)
    result = float(np.mean(values))
    return result if np.isfinite(result) and result > 0 else np.nan


def parse_area(value, numeric_factor: float = 1.0) -> float:
    text = clean_string(value).lower().replace(",", "")
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match or re.match(r"^\s*-\d", text):
        return np.nan
    area = float(match.group())
    if re.search(r"sq\.?\s*m(?:\b|t)|square\s*met|m[²2]", text):
        area *= 10.7639104167
    elif re.search(r"sq\.?\s*y|square\s*yard|yd[²2]", text):
        area *= 9
    elif "acre" in text:
        area *= 43560
    elif "hectare" in text:
        area *= 107639.104167
    elif not re.search(r"sq\.?\s*f|square\s*feet|ft[²2]", text):
        area *= numeric_factor
    return area if area > 0 and np.isfinite(area) else np.nan


def parse_floor(value) -> float:
    text = clean_string(value).lower()
    if text in {"g", "ground", "ground floor", "gf"}:
        return 0.0
    if text in {"b", "l", "lg", "basement", "lower ground", "lower ground floor"}:
        return -1.0
    match = re.search(r"-?\d+", text)
    if not match:
        return np.nan
    floor = float(match.group())
    return floor if -5 <= floor <= 150 else np.nan


def parse_age(value) -> float:
    text = clean_string(value).lower()
    if re.fullmatch(r"\d+(?:\.0)?", text):
        return AGE_CODES.get(str(int(float(text))), np.nan)
    if "under construction" in text or "new" in text or "ready to move" in text:
        return 0.0
    numbers = [float(number) for number in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return np.nan
    if len(numbers) >= 2:
        result = float(np.mean(numbers[:2]))
    elif "+" in text or "more than" in text or "above" in text:
        result = numbers[0] + 5
    else:
        result = numbers[0]
    return result if 0 <= result <= 120 else np.nan


def parse_coordinates(value) -> tuple[float, float]:
    data = parse_structured(value)
    if not isinstance(data, dict):
        return np.nan, np.nan
    data = {str(key).upper(): value for key, value in data.items()}
    try:
        lat, lon = float(data["LATITUDE"]), float(data["LONGITUDE"])
    except (KeyError, TypeError, ValueError):
        return np.nan, np.nan
    if 68 <= lat <= 97 and 8 <= lon <= 35:
        lat, lon = lon, lat
    return (lat, lon) if 8 <= lat <= 35 and 68 <= lon <= 97 else (np.nan, np.nan)


def parse_landmarks(value, total) -> tuple[float, float, float]:
    data = parse_structured(value)
    counts = {"school": 0, "hospital": 0, "transit": 0}
    entries = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        text = f"{entry.get('category', '')} {entry.get('text', '')}".lower()
        number = re.search(r"\d+", str(entry.get("text", "")))
        count = int(number.group()) if number else 1
        if re.search(r"school|education|college|university", text):
            counts["school"] += count
        if re.search(r"hospital|clinic|health", text):
            counts["hospital"] += count
        if re.search(r"metro|transit|railway|bus\s*(stop|station)|connectivity", text):
            counts["transit"] += count
    if not entries:
        try:
            total_count = float(total)
        except (ValueError, TypeError):
            total_count = 0
        total_count = float(np.clip(total_count, 0, 100)) if np.isfinite(total_count) else 0
        counts["school"] = round(total_count * 0.15)
        counts["hospital"] = round(total_count * 0.08)
        counts["transit"] = round(total_count * 0.06)
    # Landmark counts do not include radii or distances; this is an explicit proximity proxy.
    metro_proxy = max(0.3, 4.0 / (1 + counts["transit"])) if counts["transit"] else 5.0
    return float(counts["school"]), float(counts["hospital"]), metro_proxy


def coalesce(frame: pd.DataFrame, columns: list[str], parser) -> pd.Series:
    result = pd.Series(np.nan, index=frame.index, dtype=float)
    for column in columns:
        if column in frame:
            result = result.fillna(frame[column].map(parser))
    return result


def clean_source(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(path, dtype=str, low_memory=False)
    audit = {"file": path.name, "rows_loaded": len(raw), "columns": list(raw.columns)}
    for column, expected in (("RES_COM", "R"), ("PREFERENCE", "S")):
        if column in raw:
            raw = raw.loc[raw[column].fillna("").str.strip().str.upper().eq(expected)].copy()
    audit["rows_residential_sale_flags"] = len(raw)
    if "PROPERTY_TYPE" in raw:
        raw = raw.loc[normalize_key(raw["PROPERTY_TYPE"]).isin(RESIDENTIAL_TYPES)].copy()
    audit["rows_residential_dwellings"] = len(raw)
    price = coalesce(raw, ["PRICE"], parse_price)
    for column in ("MIN_PRICE", "MAX_PRICE"):
        if column in raw:
            price = price.fillna(raw[column].map(lambda value: parse_price(value, numeric_rupees=True)))
    area_factor = 1.0
    if "AREA" in raw and "MIN_AREA_SQFT" in raw:
        reference = raw["AREA"].map(parse_area)
        minimum = pd.to_numeric(raw["MIN_AREA_SQFT"], errors="coerce")
        ratios = (minimum / reference).dropna()
        if len(ratios) >= 20 and np.isclose(ratios, 0.092903, rtol=0.02).mean() >= 0.8:
            area_factor = 1 / 0.092903
    audit["min_area_sqft_numeric_factor"] = area_factor
    sqft = pd.Series(np.nan, index=raw.index, dtype=float)
    for column in ("SUPERBUILTUP_SQFT", "BUILTUP_SQFT", "AREA", "MIN_AREA_SQFT", "CARPET_SQFT"):
        if column in raw:
            factor = area_factor if column == "MIN_AREA_SQFT" else 1.0
            sqft = sqft.fillna(raw[column].map(lambda value: parse_area(value, factor)))
    locations = raw.get("location", pd.Series("", index=raw.index)).map(parse_structured)
    locality = pd.Series("", index=raw.index)
    for column in ("LOCALITY_WO_CITY", "LOCALITY"):
        if column in raw:
            values = raw[column].map(clean_string)
            locality = locality.mask(locality.eq(""), values)
    nested_locality = locations.map(lambda value: clean_string(value.get("LOCALITY_NAME", "")) if isinstance(value, dict) else "")
    locality = locality.mask(locality.eq(""), nested_locality)
    if "SOCIETY_NAME" in raw:
        locality = locality.mask(locality.eq(""), raw["SOCIETY_NAME"].map(clean_string))
    city = raw.get("CITY", pd.Series("", index=raw.index)).map(clean_string).str.title()
    locality = pd.Series([
        re.sub(rf"\s+{re.escape(city_value)}$", "", value, flags=re.IGNORECASE).strip().title()
        for value, city_value in zip(locality, city)
    ], index=raw.index)
    bedrooms = raw.get("BEDROOM_NUM", pd.Series("", index=raw.index)).str.extract(r"(\d+(?:\.\d+)?)", expand=False)
    bhk = pd.to_numeric(bedrooms, errors="coerce").clip(1, 10)
    coordinates = raw.get("MAP_DETAILS", pd.Series("", index=raw.index)).map(parse_coordinates)
    landmarks = [parse_landmarks(value, total) for value, total in zip(
        raw.get("FORMATTED_LANDMARK_DETAILS", pd.Series("", index=raw.index)),
        raw.get("TOTAL_LANDMARK_COUNT", pd.Series("", index=raw.index)),
    )]
    cleaned = pd.DataFrame({
        "source_file": path.name,
        "listing_id": raw.get("PROP_ID", pd.Series("", index=raw.index)).map(clean_string),
        "city": city, "locality": locality, "sqft": sqft, "bhk": bhk,
        "floor": raw.get("FLOOR_NUM", pd.Series("", index=raw.index)).map(parse_floor),
        "age_years": raw.get("AGE", pd.Series("", index=raw.index)).map(parse_age),
        "lat": [value[0] for value in coordinates], "lon": [value[1] for value in coordinates],
        "osm_schools_2km": [value[0] for value in landmarks],
        "osm_hospitals_2km": [value[1] for value in landmarks],
        "osm_metro_dist_km": [value[2] for value in landmarks],
        "price_lakhs": price,
    }, index=raw.index)
    audit["invalid_coordinate_rows_before_imputation"] = int(cleaned["lat"].isna().sum())
    return cleaned, audit


def impute_split(train: pd.DataFrame, test: pd.DataFrame):
    train = train.copy()
    for column, default in (("floor", 0.0), ("age_years", 5.0)):
        median = train[column].median()
        train[column] = train[column].fillna(median if pd.notna(median) else default)
    initial_lookup = build_locality_lookup(train)
    if initial_lookup[["lat", "lon"]].isna().all().any():
        raise ValueError("No valid training coordinates available; live geocoding is disabled")
    train_context = resolve_context(train, initial_lookup)
    train[CONTEXT_COLS] = train_context[CONTEXT_COLS].to_numpy()
    lookup = build_locality_lookup(train)
    test = test.copy()
    for column in ("floor", "age_years"):
        test[column] = test[column].fillna(train[column].median())
    test_context = resolve_context(test, lookup)
    test[CONTEXT_COLS] = test_context[CONTEXT_COLS].to_numpy()
    return train, test, lookup


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    sources = sorted(RAW_DIR.glob("*.csv"))
    if not sources:
        raise FileNotFoundError(f"No listing CSV files in {RAW_DIR}")
    source_hashes = {path.name: sha256(path) for path in sources}
    manifest_path = PROCESSED_DIR / "split_manifest.json"
    previous_manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if previous_manifest and previous_manifest["source_sha256"] != source_hashes:
        raise ValueError("Raw data changed. Preserve the existing locked benchmark and use a new output directory.")
    frames, audits = [], []
    for path in sources:
        frame, audit = clean_source(path)
        frames.append(frame)
        audits.append(audit)
        print(f"{path.name}: {audit['rows_loaded']:,} rows; columns={audit['columns']}")
    data = pd.concat(frames, ignore_index=True)
    counts = {"loaded": sum(audit["rows_loaded"] for audit in audits), "residential_dwellings_sale": len(data)}
    data = data.dropna(subset=["price_lakhs", "sqft", "bhk"])
    data = data.loc[data["city"].ne("") & data["locality"].ne("")].copy()
    counts["valid_required_values"] = len(data)
    data = data.loc[data["sqft"].between(300, 10000) & data["price_lakhs"].between(5, 5000)].copy()
    counts["within_absolute_bounds"] = len(data)
    has_id = data["listing_id"].ne("")
    repeated_id = data.loc[has_id].duplicated(["city", "listing_id"])
    data = data.drop(index=repeated_id[repeated_id].index).drop_duplicates(DEDUP_COLS)
    counts["deduplicated"] = len(data)
    data["price_per_sqft"] = data["price_lakhs"] * 100000 / data["sqft"]
    lower = data.groupby("city")["price_per_sqft"].transform(lambda values: values.quantile(0.02))
    upper = data.groupby("city")["price_per_sqft"].transform(lambda values: values.quantile(0.98))
    data = data.loc[data["price_per_sqft"].between(lower, upper)].copy()
    counts["within_city_2_98_percentiles"] = len(data)
    data["bhk"] = data["bhk"].round().astype(int)
    data["row_id"] = data.apply(lambda row: hashlib.sha256(
        json.dumps([row[column] if pd.notna(row[column]) else None for column in DEDUP_COLS], ensure_ascii=False).encode()
    ).hexdigest()[:20], axis=1)
    data = data.sort_values("row_id").reset_index(drop=True)
    if len(data) < 20 or data["locality"].nunique() < 2:
        raise ValueError("Not enough cleaned rows/localities for both benchmarks")
    train_random, test_random = train_test_split(data, test_size=0.2, random_state=SEED)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    train_index, test_index = next(splitter.split(data, groups=normalize_key(data["locality"])))
    outputs = {}
    splits = {}
    for name, train, test in (
        ("random", train_random, test_random),
        ("locality_heldout", data.iloc[train_index], data.iloc[test_index]),
    ):
        train, test, lookup = impute_split(train, test)
        if set(train["row_id"]) & set(test["row_id"]):
            raise AssertionError("Train/test row leakage")
        if name == "locality_heldout" and set(normalize_key(train["locality"])) & set(normalize_key(test["locality"])):
            raise AssertionError("Train/test locality leakage")
        for kind, frame in (("train", train), ("test", test)):
            outputs[f"{kind}_{name}.csv"] = frame.sort_values("row_id").to_csv(index=False, float_format="%.10g")
        if name == "random":
            outputs["localities_lookup.csv"] = lookup.to_csv(index=False, float_format="%.10g")
        splits[name] = {"train_rows": len(train), "test_rows": len(test),
                        "train_localities": train["locality"].nunique(), "test_localities": test["locality"].nunique()}
    output_hashes = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in outputs.items()}
    if previous_manifest and previous_manifest["output_sha256"] != output_hashes:
        raise ValueError("Preparation would change locked splits. Version a new benchmark instead of silently replacing them.")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (PROCESSED_DIR / name).write_text(content)
    manifest = {"seed": SEED, "source_sha256": source_hashes, "output_sha256": output_hashes,
                "row_counts": counts, "splits": splits,
                "outlier_policy": "City 2nd/98th target-rate percentiles define the full cleaned benchmark before splitting; metrics exclude those tails.",
                "imputation_policy": "Separate training-only medians for each split; no test targets used in lookup/features/model fitting.",
                "infrastructure_policy": "99acres counts and deterministic proximity proxies; not measured OSM counts, radii, or distances."}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (BASE_DIR / "logs").mkdir(exist_ok=True)
    (BASE_DIR / "logs" / "data_preparation.json").write_text(json.dumps({"sources": audits, **manifest}, indent=2) + "\n")
    print(json.dumps({"row_counts": counts, "splits": splits}, indent=2))


if __name__ == "__main__":
    main()
