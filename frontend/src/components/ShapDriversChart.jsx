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
import { HelpCircle, Sparkles, TrendingUp, TrendingDown, Info } from 'lucide-react';

export default function ShapDriversChart({ explanation, loading }) {
  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col items-center justify-center min-h-[300px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-500 mb-3"></div>
        <p className="text-xs text-slate-400">Computing SHAP tree attributions...</p>
      </div>
    );
  }

  if (!explanation || !explanation.drivers) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl flex items-center justify-center min-h-[200px] text-xs text-slate-500">
        Run a valuation to see the SHAP price drivers waterfall.
      </div>
    );
  }

  const { base_market_lakhs, predicted_price_lakhs, total_adjustment_lakhs, narrative_summary, drivers } = explanation;

  // Take top 8 drivers for clean visualization
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
        <div className="bg-slate-950 border border-slate-700 p-3 rounded-xl shadow-2xl text-xs space-y-1">
          <div className="font-bold text-white">{data.fullName}</div>
          <div className="text-slate-400">
            Observed Value: <span className="font-mono text-slate-200">{data.featureValue}</span>
          </div>
          <div className="flex items-center space-x-1 font-semibold">
            <span>Price Impact:</span>
            <span className={data.isPositive ? 'text-emerald-400' : 'text-rose-400'}>
              {data.impact > 0 ? `+₹${data.impact.toFixed(2)}` : `-₹${Math.abs(data.impact).toFixed(2)}`} Lakhs
            </span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <h3 className="font-bold text-slate-100 text-base">
            SHAP Price Drivers (Why is this home priced here?)
          </h3>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Baseline: ₹{base_market_lakhs.toFixed(1)}L ➔ ₹{predicted_price_lakhs.toFixed(1)}L
        </div>
      </div>

      {/* Narrative Explanation Callout */}
      <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 flex items-start space-x-3 text-xs leading-relaxed text-slate-300">
        <Info className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-slate-200 block mb-0.5">Automated Explainability Summary:</span>
          {narrative_summary}
        </div>
      </div>

      {/* Recharts Diverging Horizontal Bar Chart */}
      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
          >
            <XAxis
              type="number"
              domain={['auto', 'auto']}
              tickFormatter={(v) => `₹${v}L`}
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={{ stroke: '#334155' }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={140}
              tick={{ fill: '#cbd5e1', fontSize: 11 }}
              axisLine={{ stroke: '#334155' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine x={0} stroke="#64748b" strokeDasharray="3 3" />
            <Bar dataKey="impact" radius={[4, 4, 4, 4]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isPositive ? '#10b981' : '#f43f5e'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-3">
        <div className="flex items-center space-x-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 inline-block"></span>
            Value Premium (+₹)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500 inline-block"></span>
            Value Discount (-₹)
          </span>
        </div>
        <span className="text-slate-500">Tree-Explainer Exact Additive Attribution</span>
      </div>
    </div>
  );
}
