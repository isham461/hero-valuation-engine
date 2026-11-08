import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ReferenceLine,
} from 'recharts';

export default function ShapDriversChart({ explanation, loading }) {
  if (loading) {
    return (
      <div className="bg-white border border-zinc-200/90 rounded-xl p-6 shadow-sm flex flex-col items-center justify-center min-h-[260px]">
        <div className="animate-spin rounded-full h-6 w-6 border-2 border-zinc-300 border-t-zinc-800 mb-2"></div>
        <p className="text-xs text-zinc-500 font-mono">Computing SHAP feature attributions...</p>
      </div>
    );
  }

  if (!explanation || !explanation.drivers) {
    return (
      <div className="bg-white border border-zinc-200/90 rounded-xl p-6 shadow-sm flex items-center justify-center min-h-[160px] text-xs text-zinc-400 font-mono">
        Submit property specifications to calculate SHAP feature contributions.
      </div>
    );
  }

  const { base_market_lakhs, predicted_price_lakhs, narrative_summary, drivers } = explanation;

  const chartData = drivers.slice(0, 8).map((d) => ({
    name: d.display_name.length > 22 ? d.display_name.substring(0, 20) + '...' : d.display_name,
    fullName: d.display_name,
    impact: d.impact_lakhs,
    featureValue: d.feature_value,
    isPositive: d.is_positive,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white border border-zinc-200 p-2.5 rounded-lg shadow-xl text-xs space-y-1 text-zinc-900">
          <div className="font-semibold text-zinc-900">{data.fullName}</div>
          <div className="text-zinc-600 text-[11px]">
            Input: <span className="font-mono text-zinc-900 font-medium">{data.featureValue}</span>
          </div>
          <div className="flex items-center space-x-1.5 font-mono text-[11px] pt-1 border-t border-zinc-100">
            <span className="text-zinc-500">Impact:</span>
            <span className={data.isPositive ? 'text-emerald-700 font-semibold' : 'text-zinc-600 font-semibold'}>
              {data.impact > 0 ? `+₹${data.impact.toFixed(2)}` : `-₹${Math.abs(data.impact).toFixed(2)}`} Lakhs
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white border border-zinc-200/90 rounded-xl p-5 sm:p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <h3 className="font-semibold text-zinc-900 text-sm tracking-tight">
          SHAP Price Drivers
        </h3>
        <span className="text-[10px] text-zinc-500 font-mono">
          Baseline ₹{base_market_lakhs.toFixed(1)}L ➔ ₹{predicted_price_lakhs.toFixed(1)}L
        </span>
      </div>

      {/* Narrative Summary */}
      <div className="bg-zinc-50 border border-zinc-200/80 rounded-lg p-3 text-xs leading-relaxed text-zinc-700">
        <span className="text-zinc-500 font-semibold uppercase text-[10px] tracking-wider block mb-0.5">
          Underwriting Narrative
        </span>
        {narrative_summary}
      </div>

      {/* Recharts Bar Chart */}
      <div className="h-60 w-full pt-1">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 25, left: 10, bottom: 5 }}
          >
            <XAxis
              type="number"
              domain={['auto', 'auto']}
              tickFormatter={(v) => `₹${v}L`}
              tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
              axisLine={{ stroke: '#e4e4e7' }}
              tickLine={{ stroke: '#e4e4e7' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={130}
              tick={{ fill: '#3f3f46', fontSize: 11 }}
              axisLine={{ stroke: '#e4e4e7' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine x={0} stroke="#d4d4d8" strokeDasharray="2 2" />
            <Bar dataKey="impact" radius={[2, 2, 2, 2]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isPositive ? '#059669' : '#94a3b8'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between text-[11px] text-zinc-500 border-t border-zinc-100 pt-2.5">
        <div className="flex items-center space-x-3">
          <span className="flex items-center gap-1.5 text-zinc-700 font-medium">
            <span className="w-2 h-2 rounded-sm bg-emerald-600 inline-block"></span>
            Value Add (+₹)
          </span>
          <span className="flex items-center gap-1.5 text-zinc-500">
            <span className="w-2 h-2 rounded-sm bg-slate-400 inline-block"></span>
            Value Deduction (-₹)
          </span>
        </div>
        <span className="font-mono text-[10px]">Tree-Explainer Additive</span>
      </div>
    </div>
  );
}
