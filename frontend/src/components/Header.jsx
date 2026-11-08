import React from 'react';
import { Building2, ShieldCheck, Activity, Cpu } from 'lucide-react';

export default function Header({ apiStatus, activeModel, setActiveModel }) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-red-600 to-red-800 flex items-center justify-center shadow-lg shadow-red-900/30">
            <Building2 className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-red-500 font-extrabold tracking-wider text-xs uppercase bg-red-950/60 border border-red-800/60 px-2 py-0.5 rounded-full">
                Hero Housing Finance
              </span>
              <span className="text-slate-400 text-xs">Problem Statement 1</span>
            </div>
            <h1 className="text-lg font-bold text-white tracking-tight">
              PS1 Valuation & Underwriting Triage Engine
            </h1>
          </div>
        </div>

        {/* Controls & Status */}
        <div className="flex items-center space-x-3 w-full sm:w-auto justify-between sm:justify-end">
          {/* Model Toggle */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 p-1 rounded-lg text-xs">
            <button
              type="button"
              onClick={() => setActiveModel('v1')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                activeModel === 'v1'
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5" />
                v1 Benchmark <span className="text-[10px] text-slate-400">(11.8% MdAPE)</span>
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveModel('v2')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                activeModel === 'v2'
                  ? 'bg-red-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                v2 High-Precision <span className="text-[10px] text-red-200 font-semibold">(9.96% MdAPE)</span>
              </span>
            </button>
          </div>

          {/* Backend Status Badge */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border bg-slate-950/60 text-xs border-slate-800">
            <span
              className={`h-2 w-2 rounded-full ${
                apiStatus === 'healthy'
                  ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse'
                  : 'bg-amber-500'
              }`}
            />
            <span className="text-slate-300 font-mono text-[11px]">
              {apiStatus === 'healthy' ? 'API Online' : 'Connecting'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
