import React from 'react'
import { Award, Repeat, TrendingUp, Calendar } from 'lucide-react'

export const PersonalRecordsPanel: React.FC = () => {
  const records = [
    { label: 'Max Weight', val: '120 kg', icon: Award },
    { label: 'Max Reps', val: '12 reps', icon: Repeat },
    { label: 'Volume (1RM)', val: '18,240 kg', icon: TrendingUp },
    { label: 'Last Performed', val: '2 days ago', icon: Calendar },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Personal Records</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View History
        </button>
      </div>

      <div className="space-y-2.5 font-mono text-xs">
        {records.map((r, idx) => {
          const Icon = r.icon
          return (
            <div key={idx} className="flex items-center justify-between py-1 border-b border-slate-800/40 last:border-0">
              <span className="text-slate-400 flex items-center gap-2 text-[11px]">
                <Icon className="h-3.5 w-3.5 text-emerald-400" /> {r.label}
              </span>
              <span className="font-extrabold text-slate-200">{r.val}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
