import React from 'react';

export default function Header({ apiStatus, activeModel, setActiveModel }) {
  return (
    <header className="border-b border-zinc-200/90 bg-white/95 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-zinc-900 flex items-center justify-center font-mono font-bold text-xs text-white shadow-xs">
            H
          </div>
          <div>
            <div className="flex items-center space-x-1.5 text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
              <span>Hero Housing Finance</span>
              <span>·</span>
              <span>PS1 Valuation</span>
            </div>
            <h1 className="text-sm font-semibold text-zinc-900 tracking-tight">
              Automated Property Underwriting Engine
            </h1>
          </div>
        </div>

        {/* Controls & Status */}
        <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-end">
          {/* Segmented Model Switcher */}
          <div className="flex items-center bg-zinc-100 border border-zinc-200/80 p-0.5 rounded-lg text-xs">
            <button
              type="button"
              onClick={() => setActiveModel('v1')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                activeModel === 'v1'
                  ? 'bg-white text-zinc-900 shadow-xs border border-zinc-200/60 font-semibold'
                  : 'text-zinc-500 hover:text-zinc-800'
              }`}
            >
              v1 Benchmark (11.8%)
            </button>
            <button
              type="button"
              onClick={() => setActiveModel('v2')}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
                activeModel === 'v2'
                  ? 'bg-white text-zinc-900 shadow-xs border border-zinc-200/60 font-semibold'
                  : 'text-zinc-500 hover:text-zinc-800'
              }`}
            >
              v2 Precision (9.96%)
            </button>
          </div>

          {/* Backend Status Indicator */}
          <div className="flex items-center space-x-2 px-2.5 py-1 rounded-md border border-zinc-200 bg-zinc-50 text-xs text-zinc-600">
            <span
              className={`h-2 w-2 rounded-full ${
                apiStatus === 'healthy' ? 'bg-emerald-500' : 'bg-zinc-400'
              }`}
            />
            <span className="font-mono text-[11px] font-medium">
              {apiStatus === 'healthy' ? 'API Online' : 'Connecting'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
