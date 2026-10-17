import React from 'react'
import type { NutrientTargetItem } from '../../types'
import { Flame, User, Wheat, Droplet, Leaf, CircleDot, TestTube } from 'lucide-react'

export interface NutrientTargetsCardProps {
  targets: NutrientTargetItem[]
  onEditGoalsClick: () => void
}

export const NutrientTargetsCard: React.FC<NutrientTargetsCardProps> = ({ targets, onEditGoalsClick }) => {
  const getIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'calories':
        return <Flame className="h-3.5 w-3.5 text-emerald-400" />
      case 'protein':
        return <User className="h-3.5 w-3.5 text-blue-400" />
      case 'carbs':
        return <Wheat className="h-3.5 w-3.5 text-amber-400" />
      case 'fat':
        return <Droplet className="h-3.5 w-3.5 text-purple-400" />
      case 'fiber':
        return <Leaf className="h-3.5 w-3.5 text-emerald-400" />
      case 'sugar':
        return <CircleDot className="h-3.5 w-3.5 text-red-400" />
      default:
        return <TestTube className="h-3.5 w-3.5 text-cyan-400" />
    }
  }

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3.5 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Nutrient Targets</h3>
        <button
          type="button"
          onClick={onEditGoalsClick}
          className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          Edit Goals
        </button>
      </div>

      <div className="space-y-3 font-mono text-xs">
        {targets.map((item) => (
          <div key={item.name} className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getIcon(item.name)}
                <span className="font-bold text-slate-200 text-[11px]">{item.name}</span>
              </div>

              <div className="flex items-center gap-2 text-[10px]">
                <span className="text-slate-300 font-bold">
                  {item.current.toLocaleString()} / {item.target.toLocaleString()} {item.unit}
                </span>
                <span className="text-slate-400 w-8 text-right font-bold">{item.pct}%</span>
              </div>
            </div>

            <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full rounded-full"
                style={{ width: `${item.pct}%`, backgroundColor: item.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
