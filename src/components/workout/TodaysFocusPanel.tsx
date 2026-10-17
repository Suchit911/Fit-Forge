import React from 'react'
import { Target } from 'lucide-react'

export const TodaysFocusPanel: React.FC = () => {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-2 text-left">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400">
          <Target className="h-3.5 w-3.5" />
        </div>
        <h3 className="text-xs font-extrabold text-slate-100">Today's Focus</h3>
      </div>
      <p className="text-xs text-slate-300 leading-relaxed font-normal">
        Focus on controlled eccentric movement and maintain 1–2 reps in reserve on compound lifts.
      </p>
    </div>
  )
}
