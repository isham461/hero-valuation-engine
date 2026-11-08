import React from 'react';

export default function ValuationSummary({ valuation, formData }) {
  if (!valuation) return null;

  // Extract point valuation safely
  const price = Number(
    valuation.price_lakhs ??
    valuation.point_estimate ??
    valuation.estimated_value ??
    valuation.pred_val ??
    0
  );

  // Extract interval bounds: prioritize interval array (range[0], range[1]), then explicit keys
  let rangeLow = Number(
    valuation.range?.[0] ??
    valuation.prediction_interval?.[0] ??
    valuation.range_low_lakhs ??
    valuation.low_val ??
    (price * 0.90)
  );

  let rangeHigh = Number(
    valuation.range?.[1] ??
    valuation.prediction_interval?.[1] ??
    valuation.range_high_lakhs ??
    valuation.high_val ??
    (price * 1.10)
  );

  // Critical Monotonic Guard: Ensure the interval strictly wraps the point estimate
  // (P10 < Point < P90) and prevents upper bound from collapsing onto point estimate
  if (rangeHigh <= price) {
    rangeHigh = Math.round(Math.max(rangeHigh, price * 1.07) * 100) / 100;
  }
  if (rangeLow >= price) {
    rangeLow = Math.round(Math.min(rangeLow, price * 0.93) * 100) / 100;
  }

  const modelVersion = valuation.model_version || 'v1';
  const nominalCoverage = valuation.nominal_interval_coverage ?? 0.80;

  const sqft = Number(formData.sqft) || 1000;
  const ppsqft = Math.round((price * 100000) / sqft);
  const lowPpsqft = Math.round((rangeLow * 100000) / sqft);
  const highPpsqft = Math.round((rangeHigh * 100000) / sqft);

  const formatInr = (lakhs) => {
    if (lakhs >= 100) {
      return `₹${(lakhs / 100).toFixed(2)} Cr`;
    }
    return `₹${lakhs.toFixed(2)} L`;
  };

  const ltv80 = (price * 0.80).toFixed(2);
  const conservativeLtv = (rangeLow * 0.75).toFixed(2);

  const rangeSpan = rangeHigh - rangeLow;
  const pointOffsetPct = rangeSpan > 0 ? Math.min(100, Math.max(0, ((price - rangeLow) / rangeSpan) * 100)) : 50;

  return (
    <div className="bg-white border border-zinc-200/90 rounded-xl p-5 sm:p-6 shadow-sm space-y-5">
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <h3 className="font-semibold text-zinc-900 text-sm tracking-tight">
          Valuation & Underwriting Cap
        </h3>
        <span className="text-[10px] font-mono text-zinc-600 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200">
          Model: {modelVersion}
        </span>
      </div>

      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* Point Estimate */}
        <div className="bg-zinc-50 border border-zinc-200/80 rounded-lg p-4">
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-1">
            Point Valuation
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-2xl sm:text-3xl font-semibold text-zinc-900 font-mono tracking-tight">
              ₹{price.toFixed(2)}
            </span>
            <span className="text-xs font-mono text-zinc-500">Lakhs</span>
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            Equivalent: <span className="text-zinc-800 font-medium">{formatInr(price)}</span>
          </div>
          <div className="mt-3 pt-2.5 border-t border-zinc-200/80 flex justify-between text-xs text-zinc-600">
            <span>Rate / Sqft:</span>
            <span className="font-mono text-zinc-900 font-medium">₹{ppsqft.toLocaleString('en-IN')}</span>
          </div>
        </div>

        {/* Quantile Range (P10 - P90) */}
        <div className="bg-zinc-50 border border-zinc-200/80 rounded-lg p-4">
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Prediction Interval</span>
            <span className="text-[10px] text-zinc-500 font-mono">P10 – P90</span>
          </div>
          <div className="flex items-baseline space-x-1">
            <span className="text-xl sm:text-2xl font-semibold text-zinc-900 font-mono tracking-tight">
              ₹{rangeLow.toFixed(1)} – ₹{rangeHigh.toFixed(1)}
            </span>
            <span className="text-xs font-mono text-zinc-500">L</span>
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            {formatInr(rangeLow)} to {formatInr(rangeHigh)}
          </div>
          <div className="mt-3 pt-2.5 border-t border-zinc-200/80 flex justify-between text-xs text-zinc-600">
            <span>Rate Spread:</span>
            <span className="font-mono text-zinc-900 font-medium">
              ₹{lowPpsqft.toLocaleString('en-IN')} – ₹{highPpsqft.toLocaleString('en-IN')}
            </span>
          </div>
        </div>

        {/* Max Lending Cap (80% LTV) */}
        <div className="bg-zinc-50 border border-zinc-200/80 rounded-lg p-4">
          <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Max Lending Base</span>
            <span className="text-[10px] text-zinc-700 font-mono font-semibold">80% LTV</span>
          </div>
          <div className="flex items-baseline space-x-1.5">
            <span className="text-2xl sm:text-3xl font-semibold text-zinc-900 font-mono tracking-tight">
              ₹{ltv80}
            </span>
            <span className="text-xs font-mono text-zinc-500">Lakhs</span>
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">
            Collateral Sanction Cap
          </div>
          <div className="mt-3 pt-2.5 border-t border-zinc-200/80 flex justify-between text-xs text-zinc-600">
            <span>Floor (75% Low):</span>
            <span className="font-mono text-zinc-800 font-medium">₹{conservativeLtv} L</span>
          </div>
        </div>
      </div>

      {/* Uncertainty Bar */}
      <div className="bg-zinc-50 border border-zinc-200/80 rounded-lg p-3.5 space-y-2">
        <div className="flex items-center justify-between text-xs text-zinc-600">
          <span>Uncertainty Spread (Nominal Coverage: {(nominalCoverage * 100).toFixed(0)}%)</span>
          <span className="font-mono text-zinc-700 text-xs font-medium">
            ±₹{((rangeHigh - rangeLow) / 2).toFixed(2)}L (
            {(((rangeHigh - rangeLow) / price) * 100).toFixed(1)}%)
          </span>
        </div>

        <div className="relative w-full h-1.5 bg-zinc-200 rounded-full overflow-hidden">
          <div className="absolute inset-y-0 left-0 right-0 bg-zinc-300 rounded-full"></div>
          <div
            className="absolute top-0 bottom-0 w-2.5 bg-zinc-900 rounded-full transition-all duration-300"
            style={{ left: `${pointOffsetPct}%` }}
          ></div>
        </div>

        <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
          <span>P10 (Low): ₹{rangeLow.toFixed(1)}L</span>
          <span className="text-zinc-900 font-semibold">Point Valuation: ₹{price.toFixed(2)}L</span>
          <span>P90 (High): ₹{rangeHigh.toFixed(1)}L</span>
        </div>
      </div>
    </div>
  );
}
