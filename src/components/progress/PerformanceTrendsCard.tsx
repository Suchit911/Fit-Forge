import React from 'react'
import type { PerformanceTrendItem } from '../../types'
import { Dumbbell, Activity, Zap, Target } from 'lucide-react'
import { ResponsiveContainer, LineChart, Line } from 'recharts'

export interface PerformanceTrendsCardProps {
  trends: PerformanceTrendItem[]
}

export const PerformanceTrendsCard: React.FC<PerformanceTrendsCardProps> = ({ trends }) => {
  const getIcon = (iconName: string) => {
    switch (iconName) {
      case 'dumbbell':
        return <Dumbbell className="h-4 w-4 text-emerald-400" />
      case 'running':
        return <Activity className="h-4 w-4 text-emerald-400" />
      case 'lightning':
        return <Zap className="h-4 w-4 text-emerald-400" />
      default:
        return <Target className="h-4 w-4 text-emerald-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Performance Trends</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {trends.map((item) => {
          const sparkData = item.trendData.map((val, i) => ({ i, val }))

          return (
            <div
              key={item.name}
              className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 space-y-2 flex flex-col justify-between"
            >
              <div className="flex items-center gap-2">
                {getIcon(item.iconName)}
                <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-wider">
                  {item.name}
                </span>
              </div>

              <div className="space-y-0.5 font-mono">
                <span className="text-lg font-extrabold text-slate-100 block leading-none">{item.value}</span>
                <span className="text-[9px] font-bold text-emerald-400 block">{item.status}</span>
              </div>

              <div className="h-6 w-full pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sparkData}>
                    <Line type="monotone" dataKey="val" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
