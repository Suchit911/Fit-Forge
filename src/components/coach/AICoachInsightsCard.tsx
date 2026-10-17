import React from 'react'
import type { AIRecommendation } from '../../types'
import { TrendingUp, Star, AlertTriangle } from 'lucide-react'

export interface AICoachInsightsCardProps {
  insights: AIRecommendation[]
}

export const AICoachInsightsCard: React.FC<AICoachInsightsCardProps> = ({ insights }) => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'workout_adaptation':
        return <TrendingUp className="h-4 w-4 text-emerald-400 shrink-0" />
      case 'form_tip':
        return <Star className="h-4 w-4 text-amber-400 shrink-0" />
      default:
        return <AlertTriangle className="h-4 w-4 text-purple-400 shrink-0" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">AI Coach Insights</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="space-y-3 text-xs">
        {insights.map((item, idx) => (
          <div key={idx} className="flex items-start gap-2.5">
            {getIcon(item.type)}
            <div>
              <p className="text-slate-200 font-bold leading-snug">{item.title}</p>
              {item.description && (
                <p className="text-[10px] text-slate-400 mt-0.5">{item.description}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
