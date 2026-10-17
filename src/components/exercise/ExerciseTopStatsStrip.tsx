import React from 'react'
import { Dumbbell, User, Wrench, Star } from 'lucide-react'

export const ExerciseTopStatsStrip: React.FC = () => {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-left">
      {/* Stat 1: Total Exercises */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 shrink-0">
          <Dumbbell className="h-5 w-5" />
        </div>
        <div>
          <span className="text-xl font-extrabold text-slate-100 font-mono block">512</span>
          <span className="text-[10px] text-slate-400 font-mono">Total Exercises</span>
        </div>
      </div>

      {/* Stat 2: Muscle Groups */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/10 text-cyan-400 shrink-0">
          <User className="h-5 w-5" />
        </div>
        <div>
          <span className="text-xl font-extrabold text-slate-100 font-mono block">28</span>
          <span className="text-[10px] text-slate-400 font-mono">Muscle Groups</span>
        </div>
      </div>

      {/* Stat 3: Equipment Types */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 shrink-0">
          <Wrench className="h-5 w-5" />
        </div>
        <div>
          <span className="text-xl font-extrabold text-slate-100 font-mono block">6</span>
          <span className="text-[10px] text-slate-400 font-mono">Equipment Types</span>
        </div>
      </div>

      {/* Stat 4: Avg. Rating */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-4 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 shrink-0">
          <Star className="h-5 w-5 fill-amber-400" />
        </div>
        <div>
          <span className="text-xl font-extrabold text-slate-100 font-mono block">4.9</span>
          <span className="text-[10px] text-slate-400 font-mono">Avg. Rating</span>
        </div>
      </div>
    </div>
  )
}
