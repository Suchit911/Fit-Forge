import React from 'react'
import type { ProgressKpiItem } from '../../types'
import { Calendar, Dumbbell, Flame, Clock, TrendingUp } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line } from 'recharts'

export interface ProgressKpiStripProps {
  kpis: ProgressKpiItem[]
}

export const ProgressKpiStrip: React.FC<ProgressKpiStripProps> = ({ kpis }) => {
  const getIcon = (id: string) => {
    switch (id) {
      case 'k1':
        return <Calendar className="h-4 w-4 text-emerald-400" />
      case 'k2':
        return <Dumbbell className="h-4 w-4 text-blue-400" />
      case 'k3':
        return <Flame className="h-4 w-4 text-amber-400" />
      case 'k4':
        return <Clock className="h-4 w-4 text-purple-400" />
      default:
        return <TrendingUp className="h-4 w-4 text-emerald-400" />
    }
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 text-left">
      {kpis.map((kpi) => {
        const isProgressScore = kpi.id === 'k5'
        const sparkData = kpi.trendData.map((val, i) => ({ i, val }))

        return (
          <div
            key={kpi.id}
            className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-2 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 truncate">{kpi.title}</span>
              <div
                className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 shrink-0"
              >
                {getIcon(kpi.id)}
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-baseline gap-2 font-mono">
                <span className="text-2xl font-extrabold text-slate-100">{kpi.value}</span>
              </div>
              <span className="text-[10px] text-emerald-400 font-mono font-bold block">
                {kpi.changePct}
              </span>
            </div>

            {/* Sparkline or Circular Progress Ring */}
            {isProgressScore ? (
              <div className="relative flex items-center justify-end h-8">
                <svg className="h-9 w-9 transform -rotate-90">
                  <circle cx="18" cy="18" r="14" stroke="#1e293b" strokeWidth="3" fill="transparent" />
                  <circle
                    cx="18"
                    cy="18"
                    r="14"
                    stroke="#10b981"
                    strokeWidth="3"
                    strokeDasharray="88"
                    strokeDashoffset="13"
                    strokeLinecap="round"
                    fill="transparent"
                  />
                </svg>
              </div>
            ) : (
              <div className="h-6 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sparkData}>
                    <Line
                      type="monotone"
                      dataKey="val"
                      stroke={kpi.color}
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
