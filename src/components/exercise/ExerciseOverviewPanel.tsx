import React from 'react'
import { Layers, Dumbbell, Clock, Flame, Hourglass } from 'lucide-react'

export const ExerciseOverviewPanel: React.FC = () => {
  const rows = [
    { label: 'Total Sets', val: '4', icon: Layers },
    { label: 'Rep Range', val: '8–10 reps', icon: Dumbbell },
    { label: 'Rest Time', val: '90 sec', icon: Clock },
    { label: 'Calories (Est.)', val: '70–100 kcal', icon: Flame },
    { label: 'Duration', val: '3–5 min', icon: Hourglass },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <h3 className="text-sm font-extrabold text-slate-100 pb-2 border-b border-slate-800/80">
        Exercise Overview
      </h3>

      <div className="space-y-2.5 font-mono text-xs">
        {rows.map((r, idx) => {
          const Icon = r.icon
          return (
            <div key={idx} className="flex items-center justify-between py-1 border-b border-slate-800/40 last:border-0">
              <span className="text-slate-400 flex items-center gap-2 text-[11px]">
                <Icon className="h-3.5 w-3.5 text-slate-500" /> {r.label}
              </span>
              <span className="font-bold text-slate-200">{r.val}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
