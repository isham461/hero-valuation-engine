import React, { useState, useEffect } from 'react';
import { MapPin, Home, Layers, Calendar, Compass, Search, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { fetchCities, fetchLocalities } from '../services/api';

export default function ValuationForm({ formData, onChange, onSubmit, loading }) {
  const [cities, setCities] = useState([]);
  const [localitySuggestions, setLocalitySuggestions] = useState([]);
  const [showCoords, setShowCoords] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    fetchCities().then(setCities);
  }, []);

  useEffect(() => {
    if (formData.city && formData.locality && formData.locality.length >= 2) {
      fetchLocalities(formData.city, formData.locality).then(setLocalitySuggestions);
    } else {
      setLocalitySuggestions([]);
    }
  }, [formData.city, formData.locality]);

  const handleBhkChange = (bhk) => {
    onChange({ ...formData, bhk });
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-5"
    >
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Home className="w-5 h-5 text-red-500" />
          <h3 className="font-bold text-slate-100 text-base">Property Specifications</h3>
        </div>
        <span className="text-xs text-slate-400">Hero Fintech Underwriting Input</span>
      </div>

      {/* City & Locality */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-slate-400" /> City / Metro Region
          </label>
          <select
            value={formData.city}
            onChange={(e) => onChange({ ...formData, city: e.target.value })}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-red-500 transition-colors"
          >
            {cities.map((city) => (
              <option key={city} value={city}>
                {city}
              </option>
            ))}
          </select>
        </div>

        <div className="relative">
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5 text-slate-400" /> Locality / Sector
          </label>
          <input
            type="text"
            value={formData.locality}
            onChange={(e) => {
              onChange({ ...formData, locality: e.target.value });
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            placeholder="e.g. DLF Phase 5, Sector 63, Andheri West"
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-red-500 transition-colors"
            required
          />
          {showSuggestions && localitySuggestions.length > 0 && (
            <ul className="absolute z-30 left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-slate-900 border border-slate-700 rounded-xl shadow-2xl divide-y divide-slate-800 text-xs">
              {localitySuggestions.map((loc, idx) => (
                <li
                  key={idx}
                  onMouseDown={() => {
                    onChange({ ...formData, locality: loc });
                    setShowSuggestions(false);
                  }}
                  className="px-3.5 py-2 cursor-pointer hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
                >
                  {loc}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Super Built-up Area */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="text-xs font-semibold text-slate-300">
            Super Built-up Area (Sq. Ft.)
          </label>
          <div className="flex items-center space-x-1.5">
            <input
              type="number"
              min="300"
              max="10000"
              value={formData.sqft}
              onChange={(e) => onChange({ ...formData, sqft: Number(e.target.value) })}
              className="w-24 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-right text-xs font-mono font-bold text-red-400 focus:outline-none focus:border-red-500"
            />
            <span className="text-xs text-slate-500">sqft</span>
          </div>
        </div>
        <input
          type="range"
          min="400"
          max="6000"
          step="25"
          value={formData.sqft}
          onChange={(e) => onChange({ ...formData, sqft: Number(e.target.value) })}
          className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
          <span>400 sqft</span>
          <span>1,500 sqft</span>
          <span>3,000 sqft</span>
          <span>6,000 sqft</span>
        </div>
      </div>

      {/* BHK Selector */}
      <div>
        <label className="block text-xs font-semibold text-slate-300 mb-2">
          Bedrooms (BHK)
        </label>
        <div className="grid grid-cols-6 gap-2">
          {[1, 2, 3, 4, 5, 6].map((bhk) => (
            <button
              key={bhk}
              type="button"
              onClick={() => handleBhkChange(bhk)}
              className={`py-2 rounded-xl text-xs font-bold transition-all ${
                formData.bhk === bhk
                  ? 'bg-red-600 text-white shadow-md shadow-red-900/40 ring-1 ring-red-400'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              {bhk >= 6 ? '6+ BHK' : `${bhk} BHK`}
            </button>
          ))}
        </div>
      </div>

      {/* Floor & Age */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-slate-400" /> Floor Level
          </label>
          <input
            type="number"
            min="-1"
            max="100"
            value={formData.floor ?? ''}
            placeholder="e.g. 5 (Ground=0)"
            onChange={(e) =>
              onChange({
                ...formData,
                floor: e.target.value === '' ? null : Number(e.target.value),
              })
            }
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500"
          />
          <span className="text-[10px] text-slate-500 mt-0.5 block">0 = Ground, -1 = Basement</span>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-slate-400" /> Age (Years)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            step="0.5"
            value={formData.age_years ?? ''}
            placeholder="0 = New / Under Construction"
            onChange={(e) =>
              onChange({
                ...formData,
                age_years: e.target.value === '' ? null : Number(e.target.value),
              })
            }
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-red-500"
          />
          <span className="text-[10px] text-slate-500 mt-0.5 block">0 = Ready/New, 5 = 5 Years</span>
        </div>
      </div>

      {/* Advanced Indian Coordinates Collapsible */}
      <div className="border-t border-slate-800 pt-3">
        <button
          type="button"
          onClick={() => setShowCoords(!showCoords)}
          className="flex items-center justify-between w-full text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <span className="flex items-center gap-1.5 font-medium">
            <Compass className="w-3.5 h-3.5" /> Optional GPS Coordinates (Lat / Lon)
          </span>
          {showCoords ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showCoords && (
          <div className="grid grid-cols-2 gap-3 mt-3 p-3 bg-slate-950/80 rounded-xl border border-slate-800">
            <div>
              <label className="text-[11px] font-medium text-slate-400 block mb-1">
                Latitude (8.0 to 35.0)
              </label>
              <input
                type="number"
                step="0.0001"
                min="8.0"
                max="35.0"
                value={formData.lat ?? ''}
                placeholder="Auto from locality"
                onChange={(e) =>
                  onChange({
                    ...formData,
                    lat: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono"
              />
            </div>
            <div>
              <label className="text-[11px] font-medium text-slate-400 block mb-1">
                Longitude (68.0 to 97.0)
              </label>
              <input
                type="number"
                step="0.0001"
                min="68.0"
                max="97.0"
                value={formData.lon ?? ''}
                placeholder="Auto from locality"
                onChange={(e) =>
                  onChange({
                    ...formData,
                    lon: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 font-mono"
              />
            </div>
          </div>
        )}
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold py-3 px-4 rounded-xl shadow-lg shadow-red-950/50 hover:shadow-red-900/60 transition-all flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Calculating ML Valuation...</span>
          </>
        ) : (
          <span>Run Valuation & Underwriting Triage</span>
        )}
      </button>
    </form>
  );
}
