import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PresetsBar, { PRESETS } from './components/PresetsBar';
import ValuationForm from './components/ValuationForm';
import TriageBanner from './components/TriageBanner';
import ValuationSummary from './components/ValuationSummary';
import ShapDriversChart from './components/ShapDriversChart';
import ComparablesGrid from './components/ComparablesGrid';
import { fetchHealth, valuateProperty, explainProperty } from './services/api';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default function App() {
  const [activeModel, setActiveModel] = useState('v1');
  const [apiStatus, setApiStatus] = useState('connecting');
  const [currentPresetId, setCurrentPresetId] = useState('dlf-phase-5');

  const [formData, setFormData] = useState({
    city: 'Gurgaon',
    locality: 'DLF Phase 5',
    sqft: 2200,
    bhk: 3,
    floor: 8,
    age_years: 5,
    lat: null,
    lon: null,
  });

  const [valuation, setValuation] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check backend health
  useEffect(() => {
    fetchHealth().then((res) => {
      setApiStatus(res.status === 'healthy' ? 'healthy' : 'offline');
    });
  }, []);

  // Run initial valuation on mount
  useEffect(() => {
    handleRunValuation(formData, activeModel);
  }, [activeModel]);

  const handleRunValuation = async (dataToSubmit = formData, model = activeModel) => {
    setLoading(true);
    setError(null);

    const payload = {
      city: dataToSubmit.city,
      locality: dataToSubmit.locality,
      sqft: Number(dataToSubmit.sqft),
      bhk: Number(dataToSubmit.bhk),
      floor: dataToSubmit.floor !== null && dataToSubmit.floor !== '' ? Number(dataToSubmit.floor) : null,
      age_years: dataToSubmit.age_years !== null && dataToSubmit.age_years !== '' ? Number(dataToSubmit.age_years) : null,
      lat: dataToSubmit.lat !== null && dataToSubmit.lat !== '' ? Number(dataToSubmit.lat) : null,
      lon: dataToSubmit.lon !== null && dataToSubmit.lon !== '' ? Number(dataToSubmit.lon) : null,
      model_version: model,
    };

    try {
      // Run valuation and explanation in parallel
      const [valRes, expRes] = await Promise.all([
        valuateProperty(payload),
        explainProperty(payload),
      ]);

      setValuation(valRes);
      setExplanation(expRes);
    } catch (err) {
      console.error('Valuation error:', err);
      setError(err.message || 'An error occurred during valuation.');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreset = (preset) => {
    setCurrentPresetId(preset.id);
    const updated = {
      ...formData,
      ...preset.data,
      lat: null,
      lon: null,
    };
    setFormData(updated);
    handleRunValuation(updated, activeModel);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Header */}
      <Header
        apiStatus={apiStatus}
        activeModel={activeModel}
        setActiveModel={(m) => {
          setActiveModel(m);
        }}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Presets Bar */}
        <PresetsBar
          onSelectPreset={handleSelectPreset}
          currentPresetId={currentPresetId}
        />

        {/* Error Alert if any */}
        {error && (
          <div className="bg-red-950/80 border border-red-800 text-red-200 px-4 py-3 rounded-xl flex items-center justify-between text-xs shadow-lg">
            <div className="flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-white font-bold text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Two-Column Core Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Input Form (5 cols) */}
          <div className="lg:col-span-5 space-y-5 lg:sticky lg:top-20">
            <ValuationForm
              formData={formData}
              onChange={(updated) => {
                setFormData(updated);
                setCurrentPresetId(null);
              }}
              onSubmit={() => handleRunValuation(formData, activeModel)}
              loading={loading}
            />

            {/* Architecture Provenance Note */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 text-[11px] text-slate-400 space-y-2">
              <div className="font-semibold text-slate-300 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                Underwriting & System Architecture
              </div>
              <p>
                Connecting live to FastAPI backend at <code className="text-slate-300 font-mono">localhost:8000</code>.
                LightGBM quantile regression outputs natural-log price intervals [q10, q90]. The auto-accept triage gate protects
                credit approval by enforcing micro-market liquidity support.
              </p>
            </div>
          </div>

          {/* Right Column: Decisions, Metrics, SHAP, Comparables (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            {/* 1. Triage Decision Banner */}
            <TriageBanner valuation={valuation} />

            {/* 2. Valuation Summary & LTV */}
            <ValuationSummary valuation={valuation} formData={formData} />

            {/* 3. SHAP Price Drivers Waterfall Chart */}
            <ShapDriversChart explanation={explanation} loading={loading} />

            {/* 4. 3 Nearest Comparables Grid */}
            <ComparablesGrid comparables={valuation?.comparables} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-5 text-center text-xs text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Hero Housing Finance Fintech Challenge · Problem Statement 1</span>
          <span>Person 4 Deliverable · React 18 + Vite + Tailwind CSS + Recharts</span>
          <span>Dataset License: CDLA-Sharing-1.0</span>
        </div>
      </footer>
    </div>
  );
}
