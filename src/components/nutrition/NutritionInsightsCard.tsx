import React from 'react'
import type { NutritionInsightItem } from '../../types'
import { CheckCircle2, AlertTriangle, Info } from 'lucide-react'

export interface NutritionInsightsCardProps {
  insights: NutritionInsightItem[]
}

export const NutritionInsightsCard: React.FC<NutritionInsightsCardProps> = ({ insights }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Nutrition Insights</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="space-y-3 text-xs">
        {insights.map((item) => {
          const isPos = item.type === 'positive'
          const isWarn = item.type === 'warning'

          const Icon = isPos ? CheckCircle2 : isWarn ? AlertTriangle : Info
          const iconColor = isPos ? 'text-emerald-400' : isWarn ? 'text-amber-400' : 'text-cyan-400'

          return (
            <div key={item.id} className="flex items-start gap-2.5">
              <Icon className={`h-4 w-4 shrink-0 mt-0.5 ${iconColor}`} />
              <div>
                <p className="text-slate-200 font-bold leading-snug">{item.title}</p>
                {item.description && (
                  <p className="text-[10px] text-slate-400 mt-0.5">{item.description}</p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
