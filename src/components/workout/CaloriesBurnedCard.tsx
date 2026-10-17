import React from 'react'
import { Flame } from 'lucide-react'

export const CaloriesBurnedCard: React.FC = () => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center gap-2 pb-2 border-b border-slate-800/80">
        <Flame className="h-4 w-4 text-amber-400" />
        <h3 className="text-xs font-mono font-extrabold text-slate-300 uppercase tracking-wider">
          Calories Burned
        </h3>
      </div>

      <div className="flex items-baseline justify-between font-mono">
        <div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-extrabold text-slate-100">312</span>
            <span className="text-xs text-amber-400 font-bold">kcal</span>
          </div>
          <span className="text-[10px] text-slate-400 uppercase">Active Calories</span>
        </div>

        <div className="text-right">
          <span className="text-base font-bold text-slate-300 block">589</span>
          <span className="text-[10px] text-slate-500 uppercase">Total Calories</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
          <div className="h-full bg-amber-500 rounded-full" style={{ width: '53%' }} />
        </div>
        <span className="text-[10px] font-mono text-amber-400 float-right font-bold">53%</span>
      </div>
    </div>
  )
}
