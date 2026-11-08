import React from 'react';
import { Layers, MapPin, Building, Ruler, Calendar, ArrowUpRight } from 'lucide-react';

export default function ComparablesGrid({ comparables }) {
  if (!comparables || comparables.length === 0) {
    return null;
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Building className="w-5 h-5 text-red-500" />
          <h3 className="font-bold text-slate-100 text-base">
            3 Nearest Comparable Transactions / Asking Listings
          </h3>
        </div>
        <span className="text-xs text-slate-400">
          Ranked by Feature Similarity + Haversine Distance
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {comparables.map((comp, idx) => {
          const isImmediate = comp.distance_km < 1.0;
          return (
            <div
              key={comp.row_id || idx}
              className="bg-slate-950/80 border border-slate-800/90 hover:border-slate-700 rounded-xl p-4 transition-all hover:bg-slate-950 flex flex-col justify-between relative group"
            >
              {/* Card Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-bold bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
                    Comparable #{idx + 1}
                  </span>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${
                      isImmediate
                        ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800/60 font-semibold'
                        : 'bg-blue-950/80 text-blue-400 border-blue-800/60'
                    }`}
                  >
                    {comp.distance_km === 0 ? 'Exact Centroid' : `${comp.distance_km} km away`}
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white group-hover:text-red-400 transition-colors truncate">
                  {comp.locality}
                </h4>
                <p className="text-xs text-slate-400 mb-3 flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-slate-500" /> {comp.city}
                </p>

                {/* Price & Rate */}
                <div className="bg-slate-900/90 rounded-lg p-2.5 mb-3 border border-slate-800/60">
                  <div className="flex items-baseline justify-between">
                    <span className="text-lg font-extrabold text-white font-mono">
                      ₹{comp.price_lakhs.toFixed(2)} <span className="text-xs font-normal text-slate-400">Lakhs</span>
                    </span>
                    <span className="text-xs font-mono text-emerald-400 font-semibold">
                      ₹{Math.round(comp.price_per_sqft).toLocaleString('en-IN')}/sqft
                    </span>
                  </div>
                </div>

                {/* Specs */}
                <div className="grid grid-cols-2 gap-2 text-xs text-slate-300">
                  <div className="flex items-center gap-1.5 bg-slate-900/50 p-1.5 rounded">
                    <Building className="w-3.5 h-3.5 text-slate-500" />
                    <span>{comp.bhk} BHK</span>
                  </div>
                  <div className="flex items-center gap-1.5 bg-slate-900/50 p-1.5 rounded">
                    <Ruler className="w-3.5 h-3.5 text-slate-500" />
                    <span className="font-mono">{comp.sqft} sqft</span>
                  </div>
                  <div className="flex items-center gap-1.5 bg-slate-900/50 p-1.5 rounded">
                    <Layers className="w-3.5 h-3.5 text-slate-500" />
                    <span>Floor {comp.floor === 0 ? 'G' : comp.floor}</span>
                  </div>
                  <div className="flex items-center gap-1.5 bg-slate-900/50 p-1.5 rounded">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span>{comp.age_years === 0 ? 'New' : `${comp.age_years}y old`}</span>
                  </div>
                </div>
              </div>

              {/* Similarity Score footer */}
              <div className="mt-4 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                <span>Feature Distance:</span>
                <span className="font-mono text-slate-200 font-semibold">{comp.feature_distance}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
