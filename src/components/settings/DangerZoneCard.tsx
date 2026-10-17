import React from 'react'
import { AlertTriangle, Trash2 } from 'lucide-react'

export interface DangerZoneCardProps {
  onDeleteAccountClick: () => void
}

export const DangerZoneCard: React.FC<DangerZoneCardProps> = ({ onDeleteAccountClick }) => {
  return (
    <div className="rounded-3xl border border-rose-900/40 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertTriangle className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">Danger Zone</h3>
      </div>

      <div className="flex items-center justify-between p-2.5 rounded-2xl bg-rose-950/20 border border-rose-900/30 font-mono text-xs">
        <div className="flex items-center gap-2.5">
          <Trash2 className="h-4 w-4 text-rose-400" />
          <div className="space-y-0.5 font-sans">
            <h4 className="text-xs font-bold text-rose-300">Delete Account</h4>
            <p className="text-[10px] text-slate-400">Permanently delete your account and all data</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onDeleteAccountClick}
          className="rounded-xl border border-rose-500/40 bg-rose-500/10 hover:bg-rose-500 hover:text-slate-950 px-3 py-1 text-xs font-bold text-rose-400 transition-all cursor-pointer"
        >
          Delete
        </button>
      </div>
    </div>
  )
}
