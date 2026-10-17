import React from 'react'
import { Link } from 'react-router-dom'
import { MoreVertical, Clock } from 'lucide-react'
import type { Workout } from '../../types'

export interface WorkoutsTableListProps {
  workouts?: Workout[]
}

export const WorkoutsTableList: React.FC<WorkoutsTableListProps> = ({ workouts = [] }) => {
  const getDiffColor = (diff?: string) => {
    switch (diff?.toLowerCase()) {
      case 'beginner':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
      case 'advanced':
        return 'bg-red-500/10 text-red-400 border-red-500/20'
      default:
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    }
  }

  const workoutRows = workouts.map((w, idx) => ({
    id: w.id,
    title: w.title,
    desc: w.description,
    muscles: [w.targetEnvironment || 'gym'],
    duration: `${w.estimatedDurationMinutes || 45} min`,
    difficulty: w.difficulty ? w.difficulty.charAt(0).toUpperCase() + w.difficulty.slice(1) : 'Intermediate',
    diffColor: getDiffColor(w.difficulty),
    image: idx % 2 === 0 ? '/assets/dashboard_push_lifter.jpg' : '/assets/workout_lower_body.jpg',
  }))

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left space-y-4">
      {/* Table Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div>
          <h3 className="text-sm font-extrabold text-slate-100">All Workouts</h3>
          <span className="text-[10px] text-slate-400 font-mono">
            {workouts.length} workout{workouts.length === 1 ? '' : 's'} found
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">Sort by:</span>
          <select className="h-8 rounded-lg border border-slate-800 bg-slate-950 px-2.5 text-xs font-semibold text-slate-200 focus:outline-none">
            <option value="recent">Most Recent</option>
            <option value="popular">Most Popular</option>
            <option value="duration">Duration</option>
          </select>
        </div>
      </div>

      {workoutRows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400 bg-slate-950/40">
          No workouts found in library.
        </div>
      ) : (
        /* Table Rows */
        <div className="space-y-3">
          {workoutRows.map((row) => (

          <div
            key={row.id}
            className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition-colors gap-3"
          >
            {/* Title & Thumbnail */}
            <div className="flex items-center gap-3">
              <div className="h-12 w-16 rounded-lg overflow-hidden bg-slate-900 border border-slate-800 shrink-0">
                <img src={row.image} alt={row.title} className="w-full h-full object-cover opacity-80" />
              </div>
              <div>
                <Link to={`/workouts/${row.id}`} className="font-bold text-xs text-slate-100 hover:text-emerald-400 transition-colors">
                  {row.title}
                </Link>
                <p className="text-[10px] text-slate-400">{row.desc}</p>
              </div>
            </div>

            {/* Muscle Group badges */}
            <div className="hidden lg:flex items-center gap-1">
              {row.muscles.map((m, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-300 capitalize">
                  {m}
                </span>
              ))}
            </div>

            {/* Duration */}
            <div className="flex items-center gap-1 text-xs font-mono text-slate-300">
              <Clock className="h-3.5 w-3.5 text-slate-500" />
              <span>{row.duration}</span>
            </div>

            {/* Difficulty Badge */}
            <div>
              <span className={`inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold ${row.diffColor}`}>
                {row.difficulty}
              </span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Link
                to={`/workouts/${row.id}`}
                className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 hover:bg-emerald-500 hover:text-slate-950 px-3 py-1.5 text-xs font-bold text-emerald-400 transition-all cursor-pointer"
              >
                View Plan
              </Link>
              <button type="button" className="p-1 text-slate-400 hover:text-slate-200">
                <MoreVertical className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
      )}

      {/* Pagination */}
      <div className="pt-3 border-t border-slate-800/80 flex items-center justify-center gap-2 text-xs font-mono">
        <button type="button" className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200">&lt;</button>
        <button type="button" className="px-2.5 py-1 rounded bg-emerald-500 text-slate-950 font-bold">1</button>
        <button type="button" className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200">2</button>
        <button type="button" className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200">3</button>
        <button type="button" className="px-2 py-1 rounded bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200">&gt;</button>
      </div>
    </div>
  )
}
