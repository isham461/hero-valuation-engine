import React from 'react';
import { MapPin } from 'lucide-react';

export default function ComparablesGrid({ comparables }) {
  if (!comparables || comparables.length === 0) {
    return null;
  }

  return (
    <div className="bg-white border border-zinc-200/90 rounded-xl p-5 sm:p-6 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <h3 className="font-semibold text-zinc-900 text-sm tracking-tight">
          3 Nearest Comparable Listings
        </h3>
        <span className="text-[10px] font-mono text-zinc-500">
          Ranked by kNN Feature Similarity
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {comparables.map((comp, idx) => {
          return (
            <div
              key={comp.row_id || idx}
              className="bg-zinc-50/80 border border-zinc-200 hover:border-zinc-300 rounded-xl p-4 transition-colors flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[10px] font-mono text-zinc-500 font-medium">
                    Comparable #{idx + 1}
                  </span>
                  <span className="text-[10px] font-mono text-zinc-700 bg-white border border-zinc-200 px-2 py-0.5 rounded">
                    {comp.distance_km === 0 ? 'Centroid' : `${comp.distance_km} km`}
                  </span>
                </div>

                <h4 className="text-sm font-semibold text-zinc-900 truncate">
                  {comp.locality}
                </h4>
                <p className="text-xs text-zinc-500 mb-3 flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-zinc-400" /> {comp.city}
                </p>

                {/* Price & Rate */}
                <div className="bg-white rounded-md p-2.5 mb-3 border border-zinc-200/90 shadow-2xs">
                  <div className="flex items-baseline justify-between">
                    <span className="text-base font-semibold text-zinc-900 font-mono">
                      ₹{comp.price_lakhs.toFixed(2)} <span className="text-xs font-normal text-zinc-500">L</span>
                    </span>
                    <span className="text-xs font-mono text-zinc-700 font-medium">
                      ₹{Math.round(comp.price_per_sqft).toLocaleString('en-IN')}/sqft
                    </span>
                  </div>
                </div>

                {/* Specs */}
                <div className="grid grid-cols-2 gap-1.5 text-xs text-zinc-700">
                  <div className="bg-white p-1.5 rounded border border-zinc-200 text-center">
                    <span className="text-zinc-400 text-[10px] block">Layout</span>
                    <span className="font-semibold text-zinc-900">{comp.bhk} BHK</span>
                  </div>
                  <div className="bg-white p-1.5 rounded border border-zinc-200 text-center">
                    <span className="text-zinc-400 text-[10px] block">Area</span>
                    <span className="font-mono font-medium text-zinc-900">{comp.sqft} sqft</span>
                  </div>
                  <div className="bg-white p-1.5 rounded border border-zinc-200 text-center">
                    <span className="text-zinc-400 text-[10px] block">Floor</span>
                    <span className="text-zinc-900">{comp.floor === 0 ? 'Ground' : `Floor ${comp.floor}`}</span>
                  </div>
                  <div className="bg-white p-1.5 rounded border border-zinc-200 text-center">
                    <span className="text-zinc-400 text-[10px] block">Age</span>
                    <span className="text-zinc-900">{comp.age_years === 0 ? 'New' : `${comp.age_years}y`}</span>
                  </div>
                </div>
              </div>

              {/* Distance metric */}
              <div className="mt-3.5 pt-2 border-t border-zinc-200/80 flex items-center justify-between text-[10px] text-zinc-500 font-mono">
                <span>Distance Vector:</span>
                <span className="text-zinc-800 font-medium">{comp.feature_distance}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
