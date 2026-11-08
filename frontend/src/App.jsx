import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PresetsBar from './components/PresetsBar';
import ValuationForm from './components/ValuationForm';
import TriageBanner from './components/TriageBanner';
import ValuationSummary from './components/ValuationSummary';
import ShapDriversChart from './components/ShapDriversChart';
import ComparablesGrid from './components/ComparablesGrid';
import { fetchHealth, valuateProperty, explainProperty } from './services/api';
import { AlertCircle } from 'lucide-react';

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

  // Run initial valuation on mount or when model toggles
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
    <div className="min-h-screen bg-zinc-50 text-zinc-900 flex flex-col font-sans selection:bg-zinc-200">
      {/* Header */}
      <Header
        apiStatus={apiStatus}
        activeModel={activeModel}
        setActiveModel={(m) => {
          setActiveModel(m);
        }}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Presets Bar */}
        <PresetsBar
          onSelectPreset={handleSelectPreset}
          currentPresetId={currentPresetId}
        />

        {/* Error Alert if any */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-xl flex items-center justify-between text-xs shadow-sm">
            <div className="flex items-center space-x-2.5">
              <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-red-700 hover:text-red-900 font-medium text-xs transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Two-Column Minimalist Grid */}
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
            <div className="bg-white border border-zinc-200/90 rounded-xl p-4 text-[11px] text-zinc-600 shadow-sm space-y-1.5">
              <div className="font-semibold text-zinc-800 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-700"></span>
                <span>System Pipeline & Model Contract</span>
              </div>
              <p className="leading-relaxed text-zinc-500">
                LightGBM Quantile Regression models [q10, q90] running on FastAPI (<code className="text-zinc-800 font-mono bg-zinc-100 px-1 py-0.5 rounded">localhost:8000</code>). Auto-accept rule enforces 40% interval threshold and 5+ micro-market sample density.
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
      <footer className="border-t border-zinc-200 bg-white py-6 text-center text-xs text-zinc-500 mt-16">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px]">
          <span>Hero Housing Finance · PS1 Automated Underwriting Engine</span>
          <span>Hero Housing Fintech Challenge · 2-Member Team Deliverable</span>
          <span>Dataset License: CDLA-Sharing-1.0</span>
        </div>
      </footer>
    </div>
  );
}
