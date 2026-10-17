import React from 'react'
import { Dumbbell, Flame, Activity, Zap } from 'lucide-react'

export const SetRepRecommendationsSection: React.FC = () => {
  const recommendations = [
    {
      label: 'Strength',
      reps: '4–6 reps',
      sets: '4–6 sets',
      rest: '2–5 min rest',
      icon: Dumbbell,
      color: 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10',
    },
    {
      label: 'Hypertrophy',
      reps: '8–12 reps',
      sets: '3–4 sets',
      rest: '60–90 sec rest',
      icon: Flame,
      color: 'border-purple-500/30 text-purple-400 bg-purple-500/10',
    },
    {
      label: 'Endurance',
      reps: '12–20 reps',
      sets: '2–3 sets',
      rest: '30–60 sec rest',
      icon: Activity,
      color: 'border-amber-500/30 text-amber-400 bg-amber-500/10',
    },
    {
      label: 'Power',
      reps: '3–5 reps',
      sets: '3–5 sets',
      rest: '2–3 min rest',
      icon: Zap,
      color: 'border-cyan-500/30 text-cyan-400 bg-cyan-500/10',
    },
  ]

  return (
    <div className="space-y-3 text-left">
      <h3 className="text-base font-extrabold text-slate-100">Set & Rep Recommendations</h3>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {recommendations.map((item, idx) => {
          const Icon = item.icon
          return (
            <div
              key={idx}
              className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-2 flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-100">{item.label}</span>
                <div className={`flex h-7 w-7 items-center justify-center rounded-lg border ${item.color}`}>
                  <Icon className="h-3.5 w-3.5" />
                </div>
              </div>

              <div className="space-y-0.5 font-mono text-xs">
                <span className="font-extrabold text-slate-100 block">{item.reps}</span>
                <span className="text-[10px] text-slate-400 block">{item.sets}</span>
                <span className="text-[9px] text-slate-500 block">{item.rest}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
