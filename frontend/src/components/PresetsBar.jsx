import React from 'react';
import { Sparkles, CheckCircle, AlertTriangle, Building, Home } from 'lucide-react';

export const PRESETS = [
  {
    id: 'dlf-phase-5',
    title: 'Gurgaon Prime (DLF Phase 5)',
    badge: 'Auto-Accept',
    badgeType: 'success',
    desc: '3 BHK · 2,200 sqft · High Locality Support',
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
    title: 'Mumbai Metro (Andheri West)',
    badge: 'Auto-Accept',
    badgeType: 'success',
    desc: '2 BHK · 1,000 sqft · Dense Micro-Market',
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
    id: 'gurgaon-sector-63',
    title: 'Gurgaon (Sector 63 Penthouse)',
    badge: 'Luxury Triage',
    badgeType: 'warning',
    desc: '5 BHK · 3,794 sqft · Wide Interval',
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
    id: 'hyderabad-gachibowli',
    title: 'Hyderabad (Gachibowli Tech)',
    badge: 'Desktop Review',
    badgeType: 'warning',
    desc: '3 BHK · 1,800 sqft · IT Corridor',
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
    id: 'unseen-locality',
    title: 'Unseen Locality (Outskirts)',
    badge: 'Route to Valuer',
    badgeType: 'danger',
    desc: '2 BHK · 1,200 sqft · 0 Sample Fallback',
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
    title: 'Kolkata (Salt Lake Sector V)',
    badge: 'Affordable Hub',
    badgeType: 'info',
    desc: '3 BHK · 1,500 sqft · Planned Sector',
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
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-slate-200">
            One-Click Underwriting Demo Scenarios
          </h2>
        </div>
        <span className="text-xs text-slate-500 hidden sm:inline">
          Test STP auto-approvals vs. manual valuer triage
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {PRESETS.map((preset) => {
          const isSelected = currentPresetId === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => onSelectPreset(preset)}
              className={`text-left p-2.5 rounded-xl border transition-all relative overflow-hidden flex flex-col justify-between ${
                isSelected
                  ? 'border-red-500 bg-red-950/30 shadow-md shadow-red-950/40 ring-1 ring-red-500/50'
                  : 'border-slate-800 bg-slate-950/60 hover:border-slate-700 hover:bg-slate-800/50'
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-1.5">
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      preset.badgeType === 'success'
                        ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                        : preset.badgeType === 'danger'
                        ? 'bg-red-950 text-red-400 border border-red-800/60'
                        : preset.badgeType === 'warning'
                        ? 'bg-amber-950 text-amber-400 border border-amber-800/60'
                        : 'bg-blue-950 text-blue-400 border border-blue-800/60'
                    }`}
                  >
                    {preset.badge}
                  </span>
                </div>
                <div className="text-xs font-semibold text-slate-200 leading-tight">
                  {preset.title}
                </div>
              </div>
              <div className="text-[10px] text-slate-400 mt-2 truncate">
                {preset.desc}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
