import React from 'react'
import type { NotificationCategorySummary } from '../../types'
import { PieChart } from 'lucide-react'

export interface NotificationInsightsCardProps {
  insights: NotificationCategorySummary[]
}

export const NotificationInsightsCard: React.FC<NotificationInsightsCardProps> = ({ insights }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <PieChart className="h-4 w-4" />
        </div>
        <h3 className="text-sm font-extrabold text-slate-100">Notification Insights</h3>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {insights.map((item) => (
          <div key={item.category} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-300">{item.category}</span>
              <span className="text-[10px] text-slate-400 font-bold">
                {item.count} notifications ({item.percentage}%)
              </span>
            </div>
            <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${item.percentage}%`, backgroundColor: item.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
