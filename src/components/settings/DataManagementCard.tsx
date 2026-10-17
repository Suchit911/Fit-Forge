import React from 'react'
import { Database, Download, Trash2, RotateCcw } from 'lucide-react'

export interface DataManagementCardProps {
  onExportClick: () => void
  onClearClick: () => void
  onResetOnboardingClick: () => void
}

export const DataManagementCard: React.FC<DataManagementCardProps> = ({
  onExportClick,
  onClearClick,
  onResetOnboardingClick,
}) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <Database className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">Data & Management</h3>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {/* Export My Data */}
        <div className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2.5">
            <Download className="h-4 w-4 text-amber-400" />
            <div className="space-y-0.5 font-sans">
              <h4 className="text-xs font-bold text-slate-100">Export My Data</h4>
              <p className="text-[10px] text-slate-400">Download all your data</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onExportClick}
            className="rounded-xl border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500 hover:text-slate-950 px-3 py-1 text-xs font-bold text-amber-400 transition-all cursor-pointer"
          >
            Export
          </button>
        </div>

        {/* Clear Activity Data */}
        <div className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2.5">
            <Trash2 className="h-4 w-4 text-amber-400" />
            <div className="space-y-0.5 font-sans">
              <h4 className="text-xs font-bold text-slate-100">Clear Activity Data</h4>
              <p className="text-[10px] text-slate-400">This will remove all activity history</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClearClick}
            className="rounded-xl border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500 hover:text-slate-950 px-3 py-1 text-xs font-bold text-amber-400 transition-all cursor-pointer"
          >
            Clear
          </button>
        </div>

        {/* Reset Onboarding */}
        <div className="flex items-center justify-between p-2.5 rounded-2xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2.5">
            <RotateCcw className="h-4 w-4 text-amber-400" />
            <div className="space-y-0.5 font-sans">
              <h4 className="text-xs font-bold text-slate-100">Reset Onboarding</h4>
              <p className="text-[10px] text-slate-400">Retake onboarding questionnaire</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onResetOnboardingClick}
            className="rounded-xl border border-amber-500/40 bg-amber-500/10 hover:bg-amber-500 hover:text-slate-950 px-3 py-1 text-xs font-bold text-amber-400 transition-all cursor-pointer"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  )
}
