import React from 'react'
import type { AchievementKpiItem } from '../../types'
import { Trophy, Sun, Flame, Target, Gift } from 'lucide-react'

export interface AchievementKpiStripProps {
  kpis: AchievementKpiItem[]
}

export const AchievementKpiStrip: React.FC<AchievementKpiStripProps> = ({ kpis }) => {
  const getIcon = (id: string) => {
    switch (id) {
      case 'k1':
        return <Trophy className="h-4 w-4 text-emerald-400" />
      case 'k2':
        return <Sun className="h-4 w-4 text-amber-400" />
      case 'k3':
        return <Flame className="h-4 w-4 text-blue-400" />
      case 'k4':
        return <Target className="h-4 w-4 text-purple-400" />
      default:
        return <Gift className="h-4 w-4 text-orange-400" />
    }
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 text-left">
      {kpis.map((item) => (
        <div
          key={item.id}
          className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-2 flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-400 truncate">{item.title}</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 shrink-0">
              {getIcon(item.id)}
            </div>
          </div>

          <div className="space-y-1 font-mono">
            <span className="text-2xl font-extrabold text-slate-100 block leading-none">{item.value}</span>
            <span className="text-[10px] font-bold text-emerald-400 block">{item.supportingText}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
