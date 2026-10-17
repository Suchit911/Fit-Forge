import React from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, Play, Layers, Clock, Dumbbell } from 'lucide-react'
import type { Workout } from '../../types'

export interface FeaturedWorkoutsSectionProps {
  workouts?: Workout[]
}

export const FeaturedWorkoutsSection: React.FC<FeaturedWorkoutsSectionProps> = ({ workouts = [] }) => {
  const tags = ['POPULAR', 'TRENDING', 'NEW', 'FEATURED']
  const tagColors = [
    'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    'bg-purple-500/20 text-purple-400 border-purple-500/30',
    'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    'bg-amber-500/20 text-amber-400 border-amber-500/30',
  ]

  const featured = workouts.slice(0, 4).map((w, idx) => ({
    id: w.id,
    tag: tags[idx % tags.length],
    tagColor: tagColors[idx % tagColors.length],
    title: w.title,
    desc: w.description,
    exercises: w.exercises?.length || 0,
    time: w.estimatedDurationMinutes || 45,
    level: w.difficulty ? w.difficulty.charAt(0).toUpperCase() + w.difficulty.slice(1) : 'All Levels',
    image: idx % 2 === 0 ? '/assets/dashboard_push_lifter.jpg' : '/assets/workout_lower_body.jpg',
  }))

  if (featured.length === 0) {
    return null
  }

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-extrabold text-slate-100">Featured Workouts</h3>
        <button type="button" className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          View All
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {featured.map((item) => (

          <div
            key={item.id}
            className="group relative rounded-2xl border border-slate-800 bg-slate-900 overflow-hidden transition-all hover:border-slate-700 flex flex-col justify-between"
          >
            {/* Image Header */}
            <div className="relative aspect-[16/10] w-full overflow-hidden bg-slate-950">
              <img
                src={item.image}
                alt={item.title}
                className="w-full h-full object-cover opacity-80 group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent" />
              
              <span className={`absolute top-3 left-3 rounded-full border px-2 py-0.5 text-[9px] font-bold font-mono ${item.tagColor}`}>
                {item.tag}
              </span>

              <button
                type="button"
                aria-label="Bookmark workout"
                className="absolute top-3 right-3 rounded-full bg-slate-950/60 p-1.5 text-slate-300 backdrop-blur-sm hover:text-emerald-400"
              >
                <Bookmark className="h-3.5 w-3.5" />
              </button>

              <Link
                to={`/workouts/${item.id}/active`}
                className="absolute bottom-3 right-3 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 text-slate-950 shadow-md hover:scale-110 transition-transform"
              >
                <Play className="h-4 w-4 fill-slate-950 ml-0.5" />
              </Link>
            </div>

            {/* Content */}
            <div className="p-4 space-y-2">
              <Link to={`/workouts/${item.id}`} className="block">
                <h4 className="text-sm font-bold text-slate-100 hover:text-emerald-400 transition-colors">
                  {item.title}
                </h4>
              </Link>
              <p className="text-[11px] text-slate-400">{item.desc}</p>
              
              <div className="pt-2 flex items-center gap-3 text-[10px] text-slate-500 font-mono border-t border-slate-800/60">
                <span className="flex items-center gap-1"><Layers className="h-3 w-3 text-emerald-400" /> {item.exercises} Ex</span>
                <span className="flex items-center gap-1"><Clock className="h-3 w-3 text-emerald-400" /> {item.time}m</span>
                <span className="flex items-center gap-1"><Dumbbell className="h-3 w-3 text-emerald-400" /> {item.level}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
