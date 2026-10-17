import React from 'react'
import { Droplet, Plus } from 'lucide-react'

export interface WaterIntakeCardProps {
  waterLiters: number
  targetLiters: number
  onAddWater: () => void
}

export const WaterIntakeCard: React.FC<WaterIntakeCardProps> = ({
  waterLiters,
  targetLiters,
  onAddWater,
}) => {
  const totalGlasses = 10
  const pct = Math.round((waterLiters / targetLiters) * 100)
  const filledCount = Math.round((waterLiters / targetLiters) * totalGlasses)

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left shadow-2xl">
      <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
        <div className="flex items-center gap-2">
          <Droplet className="h-4 w-4 text-cyan-400 fill-cyan-400" />
          <h3 className="text-sm font-extrabold text-slate-100">Water Intake</h3>
        </div>

        <button
          type="button"
          onClick={onAddWater}
          aria-label="Add water intake"
          className="flex h-7 w-7 items-center justify-center rounded-lg border border-cyan-500/40 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500 hover:text-slate-950 transition-colors cursor-pointer"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-2">
        <div className="flex items-baseline gap-1 font-mono">
          <span className="text-2xl font-extrabold text-cyan-400">{waterLiters}</span>
          <span className="text-xs text-slate-400">/ {targetLiters} L</span>
        </div>

        {/* 10 Glass Icons */}
        <div className="grid grid-cols-10 gap-1.5 py-1">
          {Array.from({ length: totalGlasses }).map((_, idx) => {
            const isFilled = idx < filledCount
            return (
              <div
                key={idx}
                className={`h-7 rounded-md border flex items-center justify-center transition-colors ${
                  isFilled
                    ? 'bg-cyan-500/80 border-cyan-400 text-slate-950'
                    : 'bg-slate-950 border-slate-800 text-slate-700'
                }`}
              >
                <Droplet className="h-3.5 w-3.5 fill-current" />
              </div>
            )
          })}
        </div>

        <span className="text-[10px] text-slate-400 font-mono block">{pct}% of daily goal</span>
      </div>
    </div>
  )
}
