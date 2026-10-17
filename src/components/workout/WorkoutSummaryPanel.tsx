import React from 'react'
import { Dumbbell, Clock, Flame, TrendingUp, Award } from 'lucide-react'

export const WorkoutSummaryPanel: React.FC = () => {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left">
      <div className="flex items-center gap-2 pb-3 border-b border-slate-800/80">
        <Dumbbell className="h-4 w-4 text-emerald-400" />
        <h3 className="text-sm font-extrabold text-slate-100">Workout Summary</h3>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-mono">Muscle Groups</span>
          <span className="font-bold text-slate-200 block mt-0.5">Chest, Shoulders, Triceps</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-mono flex items-center gap-1">
            <Clock className="h-3 w-3 text-purple-400" /> Duration
          </span>
          <span className="font-bold text-slate-200 block mt-0.5">45 minutes</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-mono flex items-center gap-1">
            <Flame className="h-3 w-3 text-amber-400" /> Calories (Est.)
          </span>
          <span className="font-bold text-slate-200 block mt-0.5 font-mono">380–450 kcal</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block font-mono flex items-center gap-1">
            <TrendingUp className="h-3 w-3 text-cyan-400" /> Total Volume
          </span>
          <span className="font-bold text-slate-200 block mt-0.5 font-mono">18–22 sets</span>
        </div>
      </div>

      {/* Difficulty Indicator Bar */}
      <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
        <div className="flex justify-between items-center text-xs">
          <span className="text-slate-400 flex items-center gap-1 text-[11px]">
            <Award className="h-3.5 w-3.5 text-amber-400" /> Difficulty
          </span>
          <span className="font-bold text-amber-400 font-mono">Intermediate</span>
        </div>
        <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
          <div className="h-full bg-amber-400 rounded-full" style={{ width: '65%' }} />
        </div>
      </div>

    </div>
  )
}
