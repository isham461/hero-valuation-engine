import React from 'react';
import { IndianRupee, TrendingUp, ShieldAlert, Award, ArrowUpRight, Scale, BarChart3 } from 'lucide-react';

export default function ValuationSummary({ valuation, formData }) {
  if (!valuation) return null;

  const { price_lakhs, range_low_lakhs, range_high_lakhs, model_version, nominal_interval_coverage, locality_sample_count } = valuation;

  const sqft = Number(formData.sqft) || 1000;
  const ppsqft = Math.round((price_lakhs * 100000) / sqft);
  const lowPpsqft = Math.round((range_low_lakhs * 100000) / sqft);
  const highPpsqft = Math.round((range_high_lakhs * 100000) / sqft);

  // Convert to Crores if >= 100 Lakhs
  const formatInr = (lakhs) => {
    if (lakhs >= 100) {
      return `₹${(lakhs / 100).toFixed(2)} Cr`;
    }
    return `₹${lakhs.toFixed(2)} Lakhs`;
  };

  // Safe LTV calculations for lending
  const ltv80 = (price_lakhs * 0.80).toFixed(2);
  const conservativeLtv = (range_low_lakhs * 0.75).toFixed(2);

  // Relative point position in [low, high]
  const rangeSpan = range_high_lakhs - range_low_lakhs;
  const pointOffsetPct = rangeSpan > 0 ? Math.min(100, Math.max(0, ((price_lakhs - range_low_lakhs) / rangeSpan) * 100)) : 50;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Award className="w-5 h-5 text-red-500" />
          <h3 className="font-bold text-slate-100 text-base">Valuation & Risk Appraisal</h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-slate-400 text-xs font-mono bg-slate-950 px-2 py-1 rounded border border-slate-800">
            {model_version}
          </span>
        </div>
      </div>

      {/* Hero Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Point Estimate */}
        <div className="bg-gradient-to-br from-slate-950 to-slate-900/90 border border-slate-800 rounded-xl p-4 relative overflow-hidden">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Point Market Valuation
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-white tracking-tight font-mono">
              ₹{price_lakhs.toFixed(2)}
            </span>
            <span className="text-sm font-semibold text-red-400">Lakhs</span>
          </div>
          <div className="text-xs text-slate-400 mt-1 flex items-center gap-1 font-medium">
            <span>Equivalent:</span>
            <span className="text-slate-200 font-semibold">{formatInr(price_lakhs)}</span>
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex justify-between text-xs text-slate-400">
            <span>Rate / Sqft:</span>
            <span className="font-mono text-slate-200 font-semibold">₹{ppsqft.toLocaleString('en-IN')}/sqft</span>
          </div>
        </div>

        {/* Quantile Range */}
        <div className="bg-gradient-to-br from-slate-950 to-slate-900/90 border border-slate-800 rounded-xl p-4 relative overflow-hidden">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>80% Confidence Range</span>
            <span className="text-[10px] text-blue-400 bg-blue-950/60 border border-blue-800/60 px-1.5 py-0.5 rounded">
              q10 – q90
            </span>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-200 font-mono">
              ₹{range_low_lakhs.toFixed(1)} – ₹{range_high_lakhs.toFixed(1)}
            </span>
            <span className="text-xs text-slate-400">L</span>
          </div>
          <div className="text-xs text-slate-400 mt-1 font-medium">
            {formatInr(range_low_lakhs)} to {formatInr(range_high_lakhs)}
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex justify-between text-xs text-slate-400">
            <span>Rate Range:</span>
            <span className="font-mono text-slate-200">
              ₹{lowPpsqft.toLocaleString('en-IN')} – ₹{highPpsqft.toLocaleString('en-IN')}
            </span>
          </div>
        </div>

        {/* Lending LTV Base */}
        <div className="bg-gradient-to-br from-slate-950 to-slate-900/90 border border-slate-800 rounded-xl p-4 relative overflow-hidden">
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span className="flex items-center gap-1">
              <Scale className="w-3.5 h-3.5 text-emerald-400" /> Lending LTV Baseline
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded">
              80% LTV
            </span>
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-3xl font-extrabold text-emerald-400 tracking-tight font-mono">
              ₹{ltv80}
            </span>
            <span className="text-sm font-semibold text-emerald-500">Lakhs</span>
          </div>
          <div className="text-xs text-slate-400 mt-1 font-medium">
            Max Collateral Sanction Cap
          </div>
          <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex justify-between text-xs text-slate-400">
            <span>Conservative Floor (75% of Low):</span>
            <span className="font-mono text-slate-300 font-semibold">₹{conservativeLtv} L</span>
          </div>
        </div>
      </div>

      {/* Visual Interval Gauge */}
      <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
          <span>Uncertainty Gauge (Nominal Coverage: {(nominal_interval_coverage * 100).toFixed(0)}%)</span>
          <span className="font-mono text-slate-300">
            Spread: <strong className="text-white">₹{(range_high_lakhs - range_low_lakhs).toFixed(2)} Lakhs</strong> (
            {(((range_high_lakhs - range_low_lakhs) / price_lakhs) * 100).toFixed(1)}% of point)
          </span>
        </div>

        {/* Progress bar container */}
        <div className="relative w-full h-4 bg-slate-800 rounded-full overflow-hidden">
          {/* Shaded interval */}
          <div className="absolute inset-y-0 left-0 right-0 bg-gradient-to-r from-blue-900/60 via-emerald-900/60 to-blue-900/60 rounded-full"></div>
          {/* Point indicator mark */}
          <div
            className="absolute top-0 bottom-0 w-1.5 bg-red-500 shadow-md shadow-red-500 rounded-full transition-all duration-500"
            style={{ left: `${pointOffsetPct}%` }}
          ></div>
        </div>

        <div className="flex justify-between items-center text-[11px] text-slate-400 font-mono mt-1.5">
          <span>Low (q10): ₹{range_low_lakhs.toFixed(1)}L</span>
          <span className="text-red-400 font-bold">● Point: ₹{price_lakhs.toFixed(2)}L</span>
          <span>High (q90): ₹{range_high_lakhs.toFixed(1)}L</span>
        </div>
      </div>
    </div>
  );
}
