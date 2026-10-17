import React from 'react'
import { Link } from 'react-router-dom'
import { Star } from 'lucide-react'

export const SimilarExercisesPanel: React.FC = () => {
  const similar = [
    { id: 'ex_incline_db_press', name: 'Incline Barbell Press', target: 'Upper Chest', rating: 4.8, image: '/assets/workout_lower_body.jpg' },
    { id: 'ex_bench_press', name: 'Dumbbell Press', target: 'Chest', rating: 4.7, image: '/assets/dashboard_push_lifter.jpg' },
    { id: 'ex_cable_crossover', name: 'Decline Barbell Press', target: 'Lower Chest', rating: 4.6, image: '/assets/workout_hiit_ropes.jpg' },
    { id: 'ex_shoulder_press', name: 'Machine Chest Press', target: 'Chest', rating: 4.5, image: '/assets/workout_upper_pull.jpg' },
  ]

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 space-y-3 text-left">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100">Similar Exercises</h3>
        <button type="button" className="text-xs font-semibold text-emerald-400 hover:text-emerald-300">
          View All
        </button>
      </div>

      <div className="space-y-2.5">
        {similar.map((ex) => (
          <Link
            key={ex.name}
            to={`/exercises/${ex.id}`}
            className="flex items-center justify-between p-2 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors group"
          >
            <div className="flex items-center gap-2.5">
              <div className="h-10 w-12 rounded-lg overflow-hidden bg-slate-900 border border-slate-800 shrink-0">
                <img src={ex.image} alt={ex.name} className="w-full h-full object-cover opacity-80" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-100 group-hover:text-emerald-400 transition-colors">
                  {ex.name}
                </h4>
                <span className="text-[10px] text-slate-400 font-mono">{ex.target}</span>
              </div>
            </div>

            <div className="flex items-center gap-1 text-[11px] font-bold font-mono text-amber-400">
              <Star className="h-3 w-3 fill-amber-400" /> {ex.rating}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
