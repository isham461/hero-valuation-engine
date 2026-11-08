import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
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
      className="bg-white border border-zinc-200/90 rounded-xl p-5 sm:p-6 shadow-sm space-y-5"
    >
      <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
        <h3 className="font-semibold text-zinc-900 text-sm tracking-tight">
          Property Specifications
        </h3>
        <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
          Input Parameters
        </span>
      </div>

      {/* City & Locality */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">
            City / Metro
          </label>
          <select
            value={formData.city}
            onChange={(e) => onChange({ ...formData, city: e.target.value })}
            className="w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 text-xs sm:text-sm text-zinc-900 focus:outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-colors"
          >
            {cities.map((city) => (
              <option key={city} value={city} className="bg-white text-zinc-900">
                {city}
              </option>
            ))}
          </select>
        </div>

        <div className="relative">
          <label className="block text-xs font-medium text-zinc-600 mb-1.5">
            Locality / Sector
          </label>
          <input
            type="text"
            value={formData.locality}
            onChange={(e) => {
              onChange({ ...formData, locality: e.target.value });
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            placeholder="e.g. DLF Phase 5"
            className="w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 text-xs sm:text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-colors"
            required
          />
          {showSuggestions && localitySuggestions.length > 0 && (
            <ul className="absolute z-30 left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-white border border-zinc-200 rounded-lg shadow-xl divide-y divide-zinc-100 text-xs">
              {localitySuggestions.map((loc, idx) => (
                <li
                  key={idx}
                  onMouseDown={() => {
                    onChange({ ...formData, locality: loc });
                    setShowSuggestions(false);
                  }}
                  className="px-3.5 py-2 cursor-pointer hover:bg-zinc-50 text-zinc-700 hover:text-zinc-900 transition-colors"
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
          <label className="text-xs font-medium text-zinc-600">
            Super Built-up Area
          </label>
          <div className="flex items-center space-x-1">
            <input
              type="number"
              min="300"
              max="10000"
              value={formData.sqft}
              onChange={(e) => onChange({ ...formData, sqft: Number(e.target.value) })}
              className="w-20 bg-white border border-zinc-300 rounded px-2 py-0.5 text-right text-xs font-mono font-medium text-zinc-900 focus:outline-none focus:border-zinc-900"
            />
            <span className="text-xs text-zinc-500 font-mono">sqft</span>
          </div>
        </div>
        <input
          type="range"
          min="400"
          max="6000"
          step="25"
          value={formData.sqft}
          onChange={(e) => onChange({ ...formData, sqft: Number(e.target.value) })}
          className="w-full h-1.5 bg-zinc-200 rounded appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-[10px] text-zinc-400 mt-1 font-mono">
          <span>400</span>
          <span>1,500</span>
          <span>3,000</span>
          <span>6,000 sqft</span>
        </div>
      </div>

      {/* BHK Selector */}
      <div>
        <label className="block text-xs font-medium text-zinc-600 mb-1.5">
          Bedrooms (BHK)
        </label>
        <div className="grid grid-cols-6 gap-1.5">
          {[1, 2, 3, 4, 5, 6].map((bhk) => {
            const isSelected = formData.bhk === bhk;
            return (
              <button
                key={bhk}
                type="button"
                onClick={() => handleBhkChange(bhk)}
                className={`py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer border ${
                  isSelected
                    ? 'bg-zinc-900 text-white border-zinc-900 font-semibold shadow-xs'
                    : 'bg-zinc-50 border-zinc-200 text-zinc-700 hover:text-zinc-900 hover:bg-zinc-100 hover:border-zinc-300'
                }`}
              >
                {bhk >= 6 ? '6+' : `${bhk}`}
              </button>
            );
          })}
        </div>
      </div>

      {/* Floor & Age */}
      <div className="grid grid-cols-2 gap-3.5">
        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1">
            Floor Level
          </label>
          <input
            type="number"
            min="-1"
            max="100"
            value={formData.floor ?? ''}
            placeholder="0 = Ground"
            onChange={(e) =>
              onChange({
                ...formData,
                floor: e.target.value === '' ? null : Number(e.target.value),
              })
            }
            className="w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 text-xs sm:text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-zinc-900"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-zinc-600 mb-1">
            Property Age (Years)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            step="0.5"
            value={formData.age_years ?? ''}
            placeholder="0 = New"
            onChange={(e) =>
              onChange({
                ...formData,
                age_years: e.target.value === '' ? null : Number(e.target.value),
              })
            }
            className="w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 text-xs sm:text-sm text-zinc-900 placeholder-zinc-400 focus:outline-none focus:border-zinc-900"
          />
        </div>
      </div>

      {/* Coordinates Collapsible */}
      <div className="border-t border-zinc-100 pt-3">
        <button
          type="button"
          onClick={() => setShowCoords(!showCoords)}
          className="flex items-center justify-between w-full text-xs text-zinc-500 hover:text-zinc-800 transition-colors cursor-pointer"
        >
          <span>Advanced: Coordinates (Lat / Lon)</span>
          {showCoords ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showCoords && (
          <div className="grid grid-cols-2 gap-3 mt-2.5 p-3 bg-zinc-50 rounded-lg border border-zinc-200">
            <div>
              <label className="text-[11px] font-medium text-zinc-600 block mb-1">
                Latitude (8.0 to 35.0)
              </label>
              <input
                type="number"
                step="0.0001"
                min="8.0"
                max="35.0"
                value={formData.lat ?? ''}
                placeholder="Auto lookup"
                onChange={(e) =>
                  onChange({
                    ...formData,
                    lat: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                className="w-full bg-white border border-zinc-300 rounded px-2.5 py-1.5 text-xs text-zinc-900 font-mono focus:outline-none focus:border-zinc-900"
              />
            </div>
            <div>
              <label className="text-[11px] font-medium text-zinc-600 block mb-1">
                Longitude (68.0 to 97.0)
              </label>
              <input
                type="number"
                step="0.0001"
                min="68.0"
                max="97.0"
                value={formData.lon ?? ''}
                placeholder="Auto lookup"
                onChange={(e) =>
                  onChange({
                    ...formData,
                    lon: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                className="w-full bg-white border border-zinc-300 rounded px-2.5 py-1.5 text-xs text-zinc-900 font-mono focus:outline-none focus:border-zinc-900"
              />
            </div>
          </div>
        )}
      </div>

      {/* Primary Action Button */}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-zinc-900 hover:bg-black text-white font-medium py-2.5 px-4 rounded-lg shadow-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed text-xs sm:text-sm tracking-tight cursor-pointer"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-white" />
            <span>Calculating Valuation...</span>
          </>
        ) : (
          <span>Run Valuation & Underwriting</span>
        )}
      </button>
    </form>
  );
}
