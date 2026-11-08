import React from 'react';

export const PRESETS = [
  {
    id: 'dlf-phase-5',
    title: 'Gurgaon (DLF Phase 5)',
    tag: 'STP Auto-Accept',
    isAutoAccept: true,
    data: {
      city: 'Gurgaon',
      locality: 'DLF Phase 5',
      sqft: 2200,
      bhk: 3,
      floor: 8,
      age_years: 5,
    }
  },
  {
    id: 'mumbai-andheri',
    title: 'Mumbai (Andheri West)',
    tag: 'STP Auto-Accept',
    isAutoAccept: true,
    data: {
      city: 'Mumbai',
      locality: 'Andheri West',
      sqft: 1000,
      bhk: 2,
      floor: 12,
      age_years: 3,
    }
  },
  {
    id: 'hyderabad-gachibowli',
    title: 'Hyderabad (Gachibowli)',
    tag: 'Manual Review',
    isAutoAccept: false,
    data: {
      city: 'Hyderabad',
      locality: 'Gachibowli',
      sqft: 1800,
      bhk: 3,
      floor: 6,
      age_years: 1,
    }
  },
  {
    id: 'gurgaon-sector-63',
    title: 'Gurgaon (Sector 63)',
    tag: 'Wide Spread',
    isAutoAccept: false,
    data: {
      city: 'Gurgaon',
      locality: 'Sector 63',
      sqft: 3794,
      bhk: 5,
      floor: 2,
      age_years: 0.5,
    }
  },
  {
    id: 'unseen-locality',
    title: 'Sohna Rural Belt',
    tag: 'Sparse Locality',
    isAutoAccept: false,
    data: {
      city: 'Gurgaon',
      locality: 'Sohna Rural Belt',
      sqft: 1200,
      bhk: 2,
      floor: 2,
      age_years: 4,
    }
  },
  {
    id: 'kolkata-salt-lake',
    title: 'Kolkata (Salt Lake)',
    tag: 'Established Hub',
    isAutoAccept: false,
    data: {
      city: 'Kolkata',
      locality: 'Salt Lake',
      sqft: 1500,
      bhk: 3,
      floor: 4,
      age_years: 2,
    }
  }
];

export default function PresetsBar({ onSelectPreset, currentPresetId }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-zinc-200/90 rounded-xl p-2.5 sm:px-3.5 shadow-xs">
      <div className="flex items-center space-x-2 text-xs font-medium text-zinc-500 flex-shrink-0">
        <span className="font-mono text-[11px] uppercase tracking-wider font-semibold">Presets</span>
      </div>

      <div className="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
        {PRESETS.map((preset) => {
          const isSelected = currentPresetId === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => onSelectPreset(preset)}
              className={`flex-shrink-0 px-3 py-1 rounded-lg text-xs transition-colors flex items-center space-x-2 cursor-pointer border ${
                isSelected
                  ? 'bg-zinc-900 text-white border-zinc-900 font-medium shadow-xs'
                  : 'bg-zinc-50 text-zinc-600 border-zinc-200 hover:text-zinc-900 hover:bg-zinc-100 hover:border-zinc-300'
              }`}
            >
              <span>{preset.title}</span>
              <span className={`text-[10px] font-mono ${isSelected ? 'text-zinc-400' : 'text-zinc-400'}`}>
                {preset.tag}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
