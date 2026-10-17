import React from 'react'
import type { BodyCompositionStats } from '../../types'
import { Scale, Flame, Dumbbell, Activity, ArrowDown, ArrowUp } from 'lucide-react'

export interface BodyCompositionCardProps {
  stats: BodyCompositionStats
}

export const BodyCompositionCard: React.FC<BodyCompositionCardProps> = ({ stats }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="space-y-1">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100">Body Composition</h3>
          <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
            View Details
          </button>
        </div>
        <span className="text-[10px] font-mono text-slate-400 block">{stats.dateCompare}</span>
      </div>

      {/* Metrics List */}
      <div className="space-y-3 font-mono text-xs">
        {/* Weight */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-emerald-400" />
            <span className="font-bold text-slate-300">Weight</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">{stats.weightKg} kg</span>
            <span className="text-[10px] font-bold text-emerald-400 flex items-center">
              {stats.weightChangeKg} kg <ArrowDown className="h-3 w-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Body Fat */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Flame className="h-4 w-4 text-amber-400" />
            <span className="font-bold text-slate-300">Body Fat</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">{stats.bodyFatPct} %</span>
            <span className="text-[10px] font-bold text-emerald-400 flex items-center">
              {stats.bodyFatChangePct} % <ArrowDown className="h-3 w-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* Muscle Mass */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Dumbbell className="h-4 w-4 text-blue-400" />
            <span className="font-bold text-slate-300">Muscle Mass</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">{stats.muscleMassKg} kg</span>
            <span className="text-[10px] font-bold text-emerald-400 flex items-center">
              +{stats.muscleMassChangeKg} kg <ArrowUp className="h-3 w-3 ml-0.5" />
            </span>
          </div>
        </div>

        {/* BMI */}
        <div className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            <span className="font-bold text-slate-300">BMI</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-extrabold text-slate-100">{stats.bmi}</span>
            <span className="text-[10px] font-bold text-emerald-400 flex items-center">
              {stats.bmiChange} <ArrowDown className="h-3 w-3 ml-0.5" />
            </span>
          </div>
        </div>
      </div>

      {/* Goal Progress Bar */}
      <div className="space-y-1 pt-2 border-t border-slate-800/80 font-mono">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-300 font-bold">Goal Progress</span>
          <span className="text-emerald-400 font-extrabold">{stats.goalProgressPct}%</span>
        </div>
        <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
          <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${stats.goalProgressPct}%` }} />
        </div>
        <span className="text-[9px] text-slate-500 text-right block">{stats.goalKgToGo} kg to go</span>
      </div>
    </div>
  )
}
