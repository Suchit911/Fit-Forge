import React from 'react'
import type { AICoachWeeklyMetric } from '../../types'
import { Calendar, Flame, Activity, Moon } from 'lucide-react'

export interface WeeklyProgressOverviewCardProps {
  metrics: AICoachWeeklyMetric[]
}

export const WeeklyProgressOverviewCard: React.FC<WeeklyProgressOverviewCardProps> = ({ metrics }) => {
  const getIcon = (title: string) => {
    switch (title.toLowerCase()) {
      case 'workouts':
        return <Calendar className="h-3.5 w-3.5 text-emerald-400" />
      case 'calories':
        return <Flame className="h-3.5 w-3.5 text-amber-400" />
      case 'steps':
        return <Activity className="h-3.5 w-3.5 text-blue-400" />
      default:
        return <Moon className="h-3.5 w-3.5 text-purple-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Weekly Progress Overview</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View Details
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {metrics.map((item) => (
          <div
            key={item.title}
            className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 space-y-2 font-mono"
          >
            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 uppercase font-bold">
              {getIcon(item.title)} {item.title}
            </div>

            <div className="space-y-0.5">
              <div className="flex items-baseline gap-1">
                <span className="text-base font-extrabold text-slate-100">
                  {item.current.toLocaleString()}
                </span>
                <span className="text-[10px] text-slate-400">
                  / {item.target.toLocaleString()} {item.unit}
                </span>
              </div>

              <div className="flex items-center justify-between text-[9px] font-bold">
                <span style={{ color: item.color }}>{item.pct}%</span>
                <span className="text-slate-500">{item.pct}%</span>
              </div>

              <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${item.pct}%`, backgroundColor: item.color }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
