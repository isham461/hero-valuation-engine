# PS1 Valuation Engine — Frontend Dashboard

**Person 4 Deliverable** for the Hero Housing Fintech Challenge (Problem Statement 1).  
Production-ready **React 18 + Vite + Tailwind CSS + Recharts** collateral appraisal & underwriting triage interface.

---

## Features

1. **Property Input Form (`src/components/ValuationForm.jsx`)**:
   - Dynamic City selector with macro-region resolution (Gurgaon, Mumbai, Hyderabad, Kolkata).
   - Locality input with live autocomplete suggestions from `/api/v1/localities`.
   - Area slider and numeric box (300 to 10,000 sqft).
   - BHK pill buttons (1 to 6+ BHK).
   - Floor level and Building age inputs.
   - Optional Indian GPS coordinate bounds (Latitude 8–35°, Longitude 68–97°).

2. **One-Click Demo Presets (`src/components/PresetsBar.jsx`)**:
   - 🟢 **Gurgaon Prime (DLF Phase 5)**: 3 BHK, 2,200 sqft (Auto-Accept STP).
   - 🟢 **Mumbai Metro (Andheri West)**: 2 BHK, 1,000 sqft (Auto-Accept STP).
   - 🟡 **Gurgaon Sector 63 (Penthouse)**: 5 BHK, 3,794 sqft (Wide Interval Review).
   - 🟡 **Hyderabad Gachibowli**: 3 BHK, 1,800 sqft (IT Corridor Desktop Review).
   - 🔴 **Unseen Locality (Sohna Outskirts)**: 2 BHK, 1,200 sqft (Zero samples ➔ Route to Valuer).
   - 🔵 **Kolkata Salt Lake**: 3 BHK, 1,500 sqft (Planned Sector).

3. **Triage Decision Banner (`src/components/TriageBanner.jsx`)**:
   - 🟢 **AUTO-ACCEPT (STP)**: Displayed when uncertainty spread is ≤40% and locality support has ≥5 verified listings. Pre-approves collateral for digital loan sanctioning without physical inspection (87.2% historic precision).
   - 🟠 / 🔴 **ROUTE TO VALUER**: Displayed when uncertainty spread exceeds 40% or locality is unlisted/sparse (<5 listings). Surfaces specific reason codes (`insufficient_locality_support`, `wide_prediction_interval`) and prompts on-ground valuer dispatch.

4. **Valuation & LTV Appraisal Summary (`src/components/ValuationSummary.jsx`)**:
   - Point Valuation in Indian Lakhs and Crores (e.g. ₹2.16 Cr).
   - 80% Confidence Interval Range: [₹ Low — ₹ High] with visual uncertainty gauge.
   - Implied Price per Sq. Ft. rate.
   - Hero Housing Lending Guidance (80% LTV Max Sanction Cap & 75% Conservative Floor).

5. **SHAP Price Drivers Chart (`src/components/ShapDriversChart.jsx`)**:
   - Recharts horizontal diverging bar chart showing exact additive rupee adjustments (+₹ Lakhs for value premiums, -₹ Lakhs for value discounts).
   - Plain-English explainability narrative for underwriters and borrowers.

6. **3 Nearest Comparables Grid (`src/components/ComparablesGrid.jsx`)**:
   - Shows 3 nearest actual market listings ranked by feature distance and Haversine km distance.
   - Shows asking price in Lakhs, rate/sqft, BHK, sqft, floor, and age.

---

## Getting Started

### 1. Start the FastAPI Backend
From the repository root:
```bash
# In terminal 1:
source .venv/bin/activate
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Start the Frontend Dev Server
```bash
# In terminal 2:
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Production Build

```bash
cd frontend
npm run build
npm run preview
```
The optimized static bundle is generated in `frontend/dist/`.
