import React from 'react'
import type { RecentWorkoutItem } from '../../types'
import { Dumbbell } from 'lucide-react'

export interface RecentWorkoutsTableProps {
  workouts: RecentWorkoutItem[]
}

export const RecentWorkoutsTable: React.FC<RecentWorkoutsTableProps> = ({ workouts }) => {
  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left shadow-2xl h-full flex flex-col justify-between">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Recent Workouts</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono text-left">
          <thead>
            <tr className="text-[10px] text-slate-400 border-b border-slate-800/80 pb-2">
              <th className="pb-2 font-bold">Workout</th>
              <th className="pb-2 font-bold">Date</th>
              <th className="pb-2 font-bold">Duration</th>
              <th className="pb-2 font-bold">Volume</th>
              <th className="pb-2 font-bold">Calories</th>
              <th className="pb-2 font-bold text-right">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {workouts.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-400 font-sans">
                  No workout history recorded yet.
                </td>
              </tr>
            ) : (
              workouts.map((w) => (
                <tr key={w.id} className="hover:bg-slate-950/40 transition-colors group cursor-pointer">
                  <td className="py-2.5 font-bold text-slate-100 group-hover:text-emerald-400 transition-colors flex items-center gap-2">
                    <Dumbbell className="h-3.5 w-3.5 text-slate-500" /> {w.title}
                  </td>
                  <td className="py-2.5 text-slate-400">{w.date}</td>
                  <td className="py-2.5 text-slate-300">{w.durationMin} min</td>
                  <td className="py-2.5 text-slate-300">{w.volumeKg.toLocaleString()} kg</td>
                  <td className="py-2.5 text-slate-300">{w.caloriesKcal} kcal</td>
                  <td className="py-2.5 font-extrabold text-emerald-400 text-right">{w.scorePct}%</td>
                </tr>
              ))
            )}
          </tbody>

        </table>
      </div>
    </div>
  )
}
