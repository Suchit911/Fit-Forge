import React from 'react'
import { Flame, User, Wheat, Droplet } from 'lucide-react'

export interface MacroSummaryStripProps {
  consumedCalories: number
  targetCalories: number
  consumedProtein: number
  targetProtein: number
  consumedCarbs: number
  targetCarbs: number
  consumedFat: number
  targetFat: number
}

export const MacroSummaryStrip: React.FC<MacroSummaryStripProps> = ({
  consumedCalories,
  targetCalories,
  consumedProtein,
  targetProtein,
  consumedCarbs,
  targetCarbs,
  consumedFat,
  targetFat,
}) => {
  const calPct = Math.round((consumedCalories / targetCalories) * 100)
  const calRem = targetCalories - consumedCalories

  const proPct = Math.round((consumedProtein / targetProtein) * 100)
  const proRem = targetProtein - consumedProtein

  const carbPct = Math.round((consumedCarbs / targetCarbs) * 100)
  const carbRem = targetCarbs - consumedCarbs

  const fatPct = Math.round((consumedFat / targetFat) * 100)
  const fatRem = targetFat - consumedFat

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-left">
      {/* Calories */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
              <Flame className="h-4 w-4" />
            </div>
            <span className="text-xs font-bold text-slate-300">Calories</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">{calPct}%</span>
        </div>

        <div className="space-y-1">
          <div className="flex items-baseline gap-1 font-mono">
            <span className="text-xl font-extrabold text-emerald-400">{consumedCalories.toLocaleString()}</span>
            <span className="text-xs text-slate-400">/ {targetCalories.toLocaleString()} kcal</span>
          </div>

          <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${calPct}%` }} />
          </div>

          <span className="text-[10px] text-slate-500 font-mono block">{calRem} kcal remaining</span>
        </div>
      </div>

      {/* Protein */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <User className="h-4 w-4" />
            </div>
            <span className="text-xs font-bold text-slate-300">Protein</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">{proPct}%</span>
        </div>

        <div className="space-y-1">
          <div className="flex items-baseline gap-1 font-mono">
            <span className="text-xl font-extrabold text-blue-400">{consumedProtein}</span>
            <span className="text-xs text-slate-400">/ {targetProtein} g</span>
          </div>

          <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${proPct}%` }} />
          </div>

          <span className="text-[10px] text-slate-500 font-mono block">{proRem} g remaining</span>
        </div>
      </div>

      {/* Carbs */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400">
              <Wheat className="h-4 w-4" />
            </div>
            <span className="text-xs font-bold text-slate-300">Carbs</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">{carbPct}%</span>
        </div>

        <div className="space-y-1">
          <div className="flex items-baseline gap-1 font-mono">
            <span className="text-xl font-extrabold text-amber-400">{consumedCarbs}</span>
            <span className="text-xs text-slate-400">/ {targetCarbs} g</span>
          </div>

          <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div className="h-full bg-amber-500 rounded-full" style={{ width: `${carbPct}%` }} />
          </div>

          <span className="text-[10px] text-slate-500 font-mono block">{carbRem} g remaining</span>
        </div>
      </div>

      {/* Fat */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400">
              <Droplet className="h-4 w-4" />
            </div>
            <span className="text-xs font-bold text-slate-300">Fat</span>
          </div>
          <span className="text-xs font-mono font-bold text-slate-400">{fatPct}%</span>
        </div>

        <div className="space-y-1">
          <div className="flex items-baseline gap-1 font-mono">
            <span className="text-xl font-extrabold text-purple-400">{consumedFat}</span>
            <span className="text-xs text-slate-400">/ {targetFat} g</span>
          </div>

          <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
            <div className="h-full bg-purple-500 rounded-full" style={{ width: `${fatPct}%` }} />
          </div>

          <span className="text-[10px] text-slate-500 font-mono block">{fatRem} g remaining</span>
        </div>
      </div>
    </div>
  )
}
