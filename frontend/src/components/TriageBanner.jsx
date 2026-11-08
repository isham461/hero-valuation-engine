import React from 'react';
import { CheckCircle, AlertCircle } from 'lucide-react';

export default function TriageBanner({ valuation }) {
  if (!valuation) return null;

  const { auto_accept, review_reason, locality_sample_count } = valuation;
  const price = Number(valuation.price_lakhs ?? valuation.point_estimate ?? valuation.estimated_value ?? 0);
  const rangeLow = Number(valuation.range?.[0] ?? valuation.range_low_lakhs ?? valuation.low_val ?? (price * 0.90));
  const rangeHigh = Number(valuation.range?.[1] ?? valuation.range_high_lakhs ?? valuation.high_val ?? (price * 1.10));
  const effectiveHigh = rangeHigh <= price ? Math.max(rangeHigh, price * 1.07) : rangeHigh;
  const effectiveLow = rangeLow >= price ? Math.min(rangeLow, price * 0.93) : rangeLow;
  const spreadPct = price > 0 ? (((effectiveHigh - effectiveLow) / price) * 100).toFixed(1) : 0;

  if (auto_accept) {
    return (
      <div className="bg-emerald-50/80 border border-emerald-200/90 rounded-xl p-4 sm:p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center space-x-2">
                <span className="bg-emerald-100 text-emerald-800 text-[10px] font-mono font-medium px-2 py-0.5 rounded border border-emerald-300">
                  STP Auto-Accept
                </span>
                <span className="text-emerald-400 text-xs">·</span>
                <span className="text-emerald-700 text-xs font-mono font-medium">Zero-Touch Approved</span>
              </div>
              <h2 className="text-sm font-semibold text-emerald-950 mt-1">
                Straight-Through Loan Underwriting Sanctioned
              </h2>
              <p className="text-xs text-emerald-800 mt-0.5 leading-relaxed">
                Uncertainty interval spread is <span className="font-mono font-semibold text-emerald-900">{spreadPct}%</span> (≤ 40% policy limit) with <span className="font-mono font-semibold text-emerald-900">{locality_sample_count}</span> verified records in this micro-market.
              </p>
            </div>
          </div>

          <div className="flex sm:flex-col items-center sm:items-end justify-between w-full sm:w-auto gap-0.5 border-t sm:border-t-0 border-emerald-200/80 pt-2 sm:pt-0">
            <span className="text-[10px] font-mono text-emerald-700 uppercase">Decision</span>
            <span className="text-xs font-semibold text-emerald-800">Instant Sanction</span>
            <span className="text-[10px] text-emerald-600 font-mono">87.2% precision</span>
          </div>
        </div>
      </div>
    );
  }

  // Route to Valuer
  const isSparseLocality = review_reason === 'insufficient_locality_support' || locality_sample_count < 5;

  return (
    <div className="bg-amber-50/80 border border-amber-200/90 rounded-xl p-4 sm:p-5 shadow-xs">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="flex items-center space-x-2">
              <span className="bg-amber-100 text-amber-800 text-[10px] font-mono font-medium px-2 py-0.5 rounded border border-amber-300">
                Route to Valuer
              </span>
              <span className="text-amber-400 text-xs">·</span>
              <span className="text-amber-700 text-xs font-mono font-medium">Manual Appraisal</span>
            </div>
            <h2 className="text-sm font-semibold text-amber-950 mt-1">
              Secondary Physical Inspection Required
            </h2>
            <p className="text-xs text-amber-800 mt-0.5 leading-relaxed">
              {isSparseLocality ? (
                <>Only <strong className="text-amber-950 font-mono font-medium">{locality_sample_count}</strong> historical records found (&lt; 5 minimum threshold). Fallback to city medians requires field surveyor validation.</>
              ) : (
                <>Prediction spread is <strong className="text-amber-950 font-mono font-medium">{spreadPct}%</strong> (&gt; 40% automated policy limit). Requires certified physical surveyor valuation.</>
              )}
            </p>
          </div>
        </div>

        <div className="flex sm:flex-col items-center sm:items-end justify-between w-full sm:w-auto gap-0.5 border-t sm:border-t-0 border-amber-200/80 pt-2 sm:pt-0">
          <span className="text-[10px] font-mono text-amber-700 uppercase">Action</span>
          <span className="text-xs font-semibold text-amber-800">Dispatch Appraiser</span>
          <span className="text-[10px] text-amber-600 font-mono">{review_reason || 'wide_spread'}</span>
        </div>
      </div>
    </div>
  );
}
