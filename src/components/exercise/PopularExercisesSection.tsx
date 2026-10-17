import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, Star, ChevronRight, Dumbbell } from 'lucide-react'
import type { Exercise } from '../../types'

export interface PopularExercisesSectionProps {
  exercises?: Exercise[]
}

export const PopularExercisesSection: React.FC<PopularExercisesSectionProps> = ({ exercises = [] }) => {
  const [savedIds, setSavedIds] = useState<string[]>([])

  const displayItems = exercises.slice(0, 4).map((ex) => ({
    id: ex.id,
    title: ex.name,
    target: ex.primaryMuscles.map((m) => m.charAt(0).toUpperCase() + m.slice(1)).join(', '),
    rating: 4.9,
    difficulty: ex.difficulty.charAt(0).toUpperCase() + ex.difficulty.slice(1),
    equipment: ex.equipment.map((eq) => eq.replace(/_/g, ' ')).join(', ') || 'Bodyweight',
    tag: 'POPULAR',
    image: '/assets/dashboard_push_lifter.jpg',
  }))

  const toggleBookmark = (e: React.MouseEvent, id: string) => {
    e.preventDefault()
    e.stopPropagation()
    setSavedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-extrabold text-slate-100">Popular Exercises</h2>
        <button type="button" className="text-xs font-semibold text-slate-400 hover:text-slate-200">
          View All
        </button>
      </div>

      {displayItems.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400 bg-slate-900/30">
          No exercises available.
        </div>
      ) : (
        <div className="relative">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {displayItems.map((item) => {

            const isSaved = savedIds.includes(item.id)

            return (
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

                  {item.tag && (
                    <span className="absolute top-3 left-3 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 text-[9px] font-bold font-mono">
                      {item.tag}
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={(e) => toggleBookmark(e, item.id)}
                    aria-label="Bookmark exercise"
                    className={`absolute top-3 right-3 rounded-full p-1.5 backdrop-blur-sm transition-colors cursor-pointer ${
                      isSaved ? 'bg-emerald-500 text-slate-950' : 'bg-slate-950/60 text-slate-300 hover:text-emerald-400'
                    }`}
                  >
                    <Bookmark className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Content Details */}
                <div className="p-4 space-y-2">
                  <Link to={`/exercises/${item.id}`} className="block">
                    <h3 className="text-sm font-extrabold text-slate-100 hover:text-emerald-400 transition-colors">
                      {item.title}
                    </h3>
                  </Link>
                  <p className="text-[11px] font-medium text-slate-400">{item.target}</p>

                  <div className="pt-2 flex items-center justify-between text-[10px] font-mono text-slate-400 border-t border-slate-800/60">
                    <span className="flex items-center gap-1 text-amber-400 font-bold">
                      <Star className="h-3 w-3 fill-amber-400" /> {item.rating}
                    </span>
                    <span>• {item.difficulty}</span>
                    <span className="flex items-center gap-1 rounded bg-slate-950 px-1.5 py-0.5 border border-slate-800">
                      <Dumbbell className="h-3 w-3 text-slate-400" /> {item.equipment}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Carousel Chevron Indicator Right */}
        <button
          type="button"
          aria-label="Next page"
          className="absolute -right-3 top-1/2 -translate-y-1/2 hidden lg:flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 border border-slate-700 text-slate-300 shadow-xl hover:text-emerald-400 cursor-pointer"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    )}
  </div>
)
}

