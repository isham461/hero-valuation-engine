# PS1 Valuation Engine

Hero Housing Fintech Challenge — Problem Statement 1. Runnable, offline ML core with locked benchmarks, point/quantile valuation, train-only locality enrichment, and three comparable listings. Powered by a high-throughput FastAPI backend and a modern React + Vite + Tailwind CSS underwriting dashboard built by a 2-member engineering team.

## Quick start

Tested with Python 3.13.5 on macOS arm64. Use the pinned environment when loading the supplied pickle; scikit-learn/joblib models are not guaranteed compatible across library versions.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.lock.txt
```

`backend/requirements.txt` contains the requested direct dependencies; `backend/requirements.lock.txt` pins the full tested environment. On Linux, LightGBM may require the distribution's `libgomp` package. On macOS it requires OpenMP: if Homebrew is available, install `libomp`. For this workspace, which has no Homebrew, the tested alternative is the existing scikit-learn wheel's bundled runtime (set before launching Python):

```bash
export DYLD_LIBRARY_PATH="$PWD/.venv/lib/python3.13/site-packages/sklearn/.dylibs${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}"
```

Run from the repository root:

```bash
# Optional: rebuild the already supplied processed artifacts; requires the original raw CSVs.
python backend/prepare_data.py

# Raw CSVs are not needed to train from the tracked processed splits.
python backend/train.py
python -m unittest backend.test_ml_core -v
```

Training prints a Markdown evaluation table and a real sample prediction JSON, reloads the saved bundle, and verifies SHAP additivity. No network requests, live geocoding, GPU, or API keys are needed.

Inference without retraining:

```python
import joblib
from backend.features import predict_valuation

bundle = joblib.load("backend/models/valuation_bundle.pkl")
prediction = predict_valuation({
    "city": "Gurgaon",
    "locality": "Sector 63",
    "sqft": 3794,
    "bhk": 5,
    "floor": 2,
    "age_years": 0.5,
}, bundle)
print(prediction)
```

Only load trusted pickle/joblib files: loading an untrusted bundle can execute code. Load the bundle once at API startup, not on each request. `backend.features` supports package imports and the scripts also run directly from any working directory.

## Layout and Team Architecture (2-Member Team)

| Team Member | Domain & Ownership | Key Files & Responsibilities |
|---|---|---|
| **Member 1** — ML Engineering & Data Science | Core Modeling, Feature Engineering & Explainability | • Data cleaning & split locks (`backend/prepare_data.py`, `backend/data/processed/`)<br>• Feature engineering pipelines & locality lookups (`backend/features.py`, `backend/features_v2.py`)<br>• Model training: LightGBM Point + Quantile regression (`backend/train.py`, `backend/train_v2.py`)<br>• Model explainability & SHAP attribution (`backend/explain.py`)<br>• Slice benchmarks & regression tests (`backend/evaluate_slices.py`, `backend/test_ml_core.py`) |
| **Member 2** — Full-Stack Engineering & Deployment | Backend API, Underwriting Triage & Frontend Dashboard | • High-throughput FastAPI service (`backend/app.py`)<br>• Monotonic interval clamping & routing logic (`backend/routing.py`)<br>• API contract validation & security hardening (`backend/test_api.py`, `run_backend.sh`)<br>• Modern React 18 + Vite + Tailwind CSS dashboard (`frontend/`)<br>• Live autocomplete, triage banners, SHAP visualizations, and 3-comparables grid |

```text
backend/
  data/
    raw/                         # Four heavy listing CSVs ignored by Git
      facets/                    # Small original code/label dictionaries tracked
    processed/
      train_random.csv
      test_random.csv
      train_locality_heldout.csv
      test_locality_heldout.csv
      localities_lookup.csv
      split_manifest.json
      evaluation_metrics.json
      sample_prediction.json
  models/valuation_bundle.pkl
  logs/data_preparation.json
  logs/training_summary.txt
  features.py
  prepare_data.py
  train.py
  test_ml_core.py
  requirements.txt
  requirements.lock.txt
frontend/README.md
```

Processed CSVs, metrics, logs, facet dictionaries, and the compressed model bundle are intentionally Git-trackable. Raw listing CSVs, virtual environments, caches, `.env`, and Node dependencies are ignored. The raw files originally arrived in `archive/` and were moved into `backend/data/raw/`.

A local `main` Git repository has been initialized. No commit, remote, or GitHub push is created by the ML scripts. Publishing requires the team's chosen GitHub repository and an authorized commit/push; teammates cannot pull these local changes until then.

## Dataset, license, and provenance

Source: Kaggle dataset `arvanshul/gurgaon-real-estate-99acres-com` (99acres real-estate listings), supplied under **CDLA-Sharing-1.0**. Retain the original provider/source attribution and the CDLA-Sharing-1.0 license notice when redistributing the raw or derived dataset; consult that license before redistribution. This README does not assign a separate software/model license.

The provided archive contains `gurgaon_10k.csv`, `hyderabad.csv`, `kolkata.csv`, and `mumbai.csv` (38,502 rows combined), plus facet dictionaries. The primary benchmark includes all four files, not just Gurgaon. City names retain the source's metro subregions, such as `Kolkata South` and `Navi Mumbai`; clients should use names from the lookup rather than inventing aliases. No contact names, phone numbers, broker photos, descriptions, or image URLs are propagated to processed artifacts.

These are historical listing **asking prices** from the 2023 exports, not verified transactions or current market appraisals. They are not suitable for autonomous lending decisions.

### Cleaning rules and known source quirks

- Apply `RES_COM == R` and `PREFERENCE == S` per source when those columns exist. A dwelling-type allowlist also excludes commercial/unknown types and residential land: a BHK dwelling model cannot meaningfully value bare plots. Drop missing BHK rather than inventing rooms; clip valid parsed BHK to 1–10.
- Prefer `PRICE`, then valid `MIN_PRICE`, then `MAX_PRICE`. Parse crore/lakh/L strings, raw INR amounts, comma-separated numbers, and price ranges; explicit MIN/MAX numeric values are INR. Bare PRICE values at least 10,000 are treated as rupees; smaller unitless values as lakhs. Invalid/nonpositive prices are excluded.
- Coalesce `SUPERBUILTUP_SQFT`, `BUILTUP_SQFT`, `AREA`, `MIN_AREA_SQFT`, `CARPET_SQFT`. Parse square metres/yards/acres when explicit. Despite its name, `MIN_AREA_SQFT` is square metres in multiple exports: infer a conversion only when at least 20 paired AREA values exist and at least 80% match the 0.092903 ratio. Record this decision per file in the preparation log. Fallback area bases are mixed and remain a source of uncertainty.
- Locality priority is `LOCALITY_WO_CITY`, `LOCALITY`, nested `location.LOCALITY_NAME`, then `SOCIETY_NAME`. The nested field is essential for Mumbai/Hyderabad/Kolkata and avoids mistaking every society for a locality. Clean whitespace/case and strip redundant city suffixes. Lookup keys use lowercase stripped city/locality pairs.
- Facet-backed AGE codes: `1 → 3`, `2 → 7.5`, `3 → 15`, `5 → 0` (under construction), `6 → 0.5` years. Code `0` and unknown codes are missing; explicit year strings/ranges are parsed separately. Floor `G → 0`; `B/L → -1`; unknown/multistoried values are missing. Missing floor/age use training medians, independently per split.
- Safely parse JSON/Python literal MAP_DETAILS, swap inverted coordinates, require latitude 8–35 and longitude 68–97, and fill from training locality, training city, then global training locality medians. No evaluation row contributes to coordinate imputation or lookup targets.
- `osm_schools_2km` and `osm_hospitals_2km` are parsed landmark counts, not measured 2 km OSM counts. If structured details are absent, use 15% and 8% of capped TOTAL_LANDMARK_COUNT. Transit mentions include metro/rail/bus/connectivity; the synthetic proximity proxy is `max(0.3, 4 / (1 + transit_count))` km or 5 km when absent (missing-detail transit count uses 6% of total). The `osm_*` names preserve the integration contract only. Do not claim these are real OSM observations.
- Deduplicate repeated `(city, listing_id)` and `(city, locality, sqft, bhk, floor, price_lakhs)` tuples. Keep 300–10,000 sqft and 5–5,000 lakhs, then retain city-specific 2nd–98th price-per-sqft percentiles. The result is **24,244 rows**.

**Benchmark selection caveat:** as requested, target-derived city percentile trimming happens on the full cleaned population before splitting. These metrics describe that preselected population, not an untouched real-world holdout or the excluded tails. All model fitting, baseline rate estimates, residual intervals, locality lookup, and missing-value imputation use only each split's training rows. Unidentified near-duplicate listings may still remain.

## Locked splits and train-only lookup

Seed 42; stable row IDs and sorting; raw/output SHA-256 checksums in `split_manifest.json`.

| Split | Train rows | Test rows | Train locality names | Test locality names |
|---|---:|---:|---:|---:|
| Random | 19,395 | 4,849 | 1,518 | 857 |
| Locality held out | 19,495 | 4,749 | 1,340 | 335 |

`GroupShuffleSplit` holds out 20% of normalized locality names, so the row fraction is approximate. Names shared across cities stay in the same partition. No locality name or stable row ID overlaps the held-out training/test sets. Each benchmark's three LightGBM models and two baselines are fitted independently; the random-trained model is **not** reused to score the locality holdout.

Preparation refuses changed raw hashes or regenerated split hashes rather than silently redefining the benchmark. Training verifies all tracked input checksums before fitting. Preserve/version the benchmark in a separate checkout/output directory for intentional data or cleaning changes.

`localities_lookup.csv` is aggregated **only from train_random** and contains `city_key`, `locality_key`, `city`, `locality`, median `lat`, `lon`, three infrastructure proxies, `locality_sample_count`, and `locality_median_ppsqft`. Extra `floor`/`age_years` medians support missing API attributes. The locality rate is a baseline/support field, **never** a LightGBM feature. Held-out evaluation builds its own training-only lookup in memory.

## Features, models, and comparables

The single source of truth is `backend/features.py`:

```python
FEATURE_COLS = [
    "sqft", "bhk", "floor", "age_years", "lat", "lon",
    "osm_schools_2km", "osm_hospitals_2km", "osm_metro_dist_km",
    "sqft_per_bhk", "is_high_floor", "amenity_index",
]
```

`build_features(df, localities_df)` preserves row order/index, normalizes lookup keys, fills only missing context, and returns finite numeric columns in exactly that order. `sqft_per_bhk = sqft / bhk`; high floor means floor ≥10; amenity index is schools + 1.5×hospitals + 2/(1+metro proxy).

Three `LGBMRegressor`s learn **natural-log price in lakhs**: point uses L1 regression; lower/upper use quantile objectives at 0.1/0.9. Always exponentiate predictions. Independently fitted quantiles can cross or miss the point estimate, so served intervals use the minimum/maximum of the two quantiles and point. These are nominal 80% ranges, not guaranteed coverage.

The production bundle contains the random-trained `model_point`, `model_low`, `model_high`, fitted `scaler`, `nn` (`NearestNeighbors(n_neighbors=3)`), training-only `comparables`, `localities_lookup`, exact `feature_cols`, `target_transform`, model version, training/source checksums, library versions, and auto-accept policy.

`get_3_comparables(input_row_dict, X_row_df, bundle)` retrieves up to 100 standardized-feature neighbors, filters to the same city, expands its search if fewer than three eligible candidates remain, and re-ranks by feature distance + min(Haversine km / 5, 20). A supplied `row_id` excludes itself. It returns up to three distinct training listings, never test listings; a city with fewer eligible examples can return fewer. Coordinates shared at locality centroids can produce zero distance; this does not establish that two listings are the same building.

SHAP explanations apply in **log-price space**; feature contributions must not be presented as additive lakhs. Training/tests verify that the SHAP base value plus contributions equals the model's log prediction.

## Verified evaluation

| Split | Model | MdAPE % | Within ±10% | Within ±20% | Auto-Accept |
|---|---|---:|---:|---:|---:|
| Random | Locality median sqft rate | 14.39 | 37.86% | 61.72% | 0.00% |
| Random | Ridge regression | 30.29 | 16.75% | 33.70% | 0.00% |
| Random | LightGBM + quantiles | 11.78 | 44.63% | 69.58% | 25.82% |
| Locality held out | Locality median sqft rate | 29.61 | 18.24% | 36.41% | 0.00% |
| Locality held out | Ridge regression | 34.06 | 14.02% | 28.66% | 0.00% |
| Locality held out | LightGBM + quantiles | 18.56 | 29.59% | 53.36% | 0.00% |

MdAPE = median(abs(actual−prediction)/actual)×100. The locality baseline multiplies training locality median sqft rate by area, falling back to training city/global rates. Ridge uses the same features with StandardScaler and log-price targets. Baseline intervals use training-only 5-fold out-of-fold log residual quantiles.

Auto-accept is a transparent demonstration policy: `(high-low)/point <= 0.40` **and** at least five training listings in the exact city/locality. It never looks at the true test price. Unseen localities always require review; broad baseline intervals yield zero auto-accept. This is not a lending approval rule. Random LightGBM accepts 1,252/4,849 rows; 87.22% of accepted predictions fall within ±20%, so even accepted results can be wrong.

The primary benchmark uses available listing coordinates/proxies. A minimal API request instead fills them from the training lookup: random-split MdAPE is **13.22%**, within ±20% is **65.81%**. Both paths and per-city breakdowns are saved in `evaluation_metrics.json`. Random LightGBM interval coverage is **74.37%**, below the nominal 80%; do not advertise calibrated coverage. Do not tune parameters or thresholds against these locked test sets; use a separate training-only validation/calibration split for future improvements.

## Implemented FastAPI backend

The FastAPI backend implements the following routes using the shared `predict_valuation(request_dict, bundle)` helper:

- `POST /api/v1/valuate` — validate a property request and return its valuation.
- `GET /api/v1/cities` — list supported cities.
- `GET /api/v1/localities` — search localities within a city.
- `GET /health` — report API and model availability.

The API validates requests with Pydantic, loads trusted model bundles at startup, and does not perform live geocoding.

| Request field | Type / contract |
|---|---|
| `city` | Required nonempty string; must be a city in the training lookup, case/whitespace insensitive |
| `locality` | Required nonempty string; unknown names use provided coordinates or training city fallback and force review |
| `sqft` | Required finite number, 300–10,000; dwelling area in square feet |
| `bhk` | Required integer, 1–10 |
| `floor` | Optional finite number, −5–150; ground 0, basement −1; missing uses training context |
| `age_years` | Optional finite number, 0–120; actual years, **not** raw 99acres AGE codes |
| `lat`, `lon` | Optional pair of finite Indian coordinates; omit both to use the static training lookup |

Use Pydantic boundary validation, reject unknown fields, and map invalid/unsupported requests to HTTP 422 with `{"detail": "..."}`. Return HTTP 503 if a verified trusted model bundle is unavailable. Infrastructure proxies are server-enriched, not a required public input. No live geocoding is needed.

Actual sample request:

```json
{"city":"Gurgaon","locality":"Sector 63","sqft":3794,"bhk":5,"floor":2,"age_years":0.5}
```

Actual response values: `price_lakhs: 580.17`, `range_low_lakhs: 390.06`, `range_high_lakhs: 723.03`, `auto_accept: false`, `review_reason: "wide_prediction_interval"`, `locality_sample_count: 72`. The full JSON with three comparables is in `backend/data/processed/sample_prediction.json` and the terminal log.

Response keys:

- `model_version`, `currency: "INR"`, `unit: "lakh"`.
- `price_lakhs`, `range_low_lakhs`, `range_high_lakhs`: ordered positive numbers rounded to two decimals.
- `nominal_interval_coverage`: model-specific nominal interval coverage (0.8 for v1, 0.84 for v2), `auto_accept`, nullable `review_reason` (`insufficient_locality_support` or `wide_prediction_interval`).
- `locality_sample_count`, `location_source`, `infrastructure_source` indicate support/fallback and that landmarks are proxies.
- `comparables`: up to three objects containing `row_id`, `city`, `locality`, `sqft`, `bhk`, `floor`, `age_years`, `lat`, `lon`, `price_lakhs`, `price_per_sqft` (INR/sqft), `distance_km`, and `feature_distance`.

The underwriting dashboard displays the nominal confidence range, review triage reasons, and comparable asking prices, ensuring `auto_accept` functions as a collateral appraisal check rather than full credit sanctioning.

## Running and testing the API

Install the project dependencies from the locked requirements file:

```bash
python -m pip install -r backend/requirements.lock.txt
```

Start the FastAPI server from the project root:

```bash
python -m uvicorn backend.app:app --reload
```

The API is available at `http://127.0.0.1:8000`.

Interactive API documentation: `http://127.0.0.1:8000/docs`

### API endpoints

- `GET /health`
- `GET /api/v1/cities`
- `GET /api/v1/localities?city=Gurgaon`
- `POST /api/v1/valuate`

### Running API tests

Run the API contract tests:

```bash
python -m unittest backend.test_api -v
```

Run the complete backend test suite, including ML core tests:

```bash
python -m unittest discover -s backend -v
```
