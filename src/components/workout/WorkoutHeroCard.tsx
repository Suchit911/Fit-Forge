import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Play, Bookmark, Share2, MoreVertical, Layers, Clock, Dumbbell } from 'lucide-react'

export interface WorkoutHeroCardProps {
  workoutId: string
  title: string
  subtitle: string
  environment: string
  exerciseCount: number
  duration: number
  difficulty: string
  description: string
  image: string
}

export const WorkoutHeroCard: React.FC<WorkoutHeroCardProps> = ({
  workoutId,
  title,
  subtitle,
  environment,
  exerciseCount,
  duration,
  difficulty,
  description,
  image,
}) => {
  const [isSaved, setIsSaved] = useState(false)

  return (
    <div className="relative rounded-3xl border border-slate-800 bg-slate-900 overflow-hidden shadow-2xl text-left">
      <div className="grid grid-cols-1 lg:grid-cols-12 items-center">
        
        {/* Left Information & Actions Column (7 cols) */}
        <div className="lg:col-span-7 p-6 sm:p-8 space-y-5">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">
              {title}
            </h1>
            <p className="text-sm font-semibold text-slate-400 mt-1">
              {subtitle}
            </p>
          </div>

          {/* Badges Row */}
          <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
            <span className="rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 font-bold uppercase tracking-wider">
              {environment}
            </span>
            <span className="flex items-center gap-1 text-slate-300">
              <Layers className="h-3.5 w-3.5 text-emerald-400" /> {exerciseCount} Exercises
            </span>
            <span className="flex items-center gap-1 text-slate-300">
              <Clock className="h-3.5 w-3.5 text-emerald-400" /> {duration} min
            </span>
            <span className="flex items-center gap-1 text-slate-300">
              <Dumbbell className="h-3.5 w-3.5 text-emerald-400" /> {difficulty}
            </span>
          </div>

          {/* Description */}
          <p className="text-xs text-slate-400 leading-relaxed max-w-xl">
            {description}
          </p>

          {/* Action Buttons Row */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              to={`/workouts/${workoutId}/active`}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-6 py-2.5 text-xs font-extrabold shadow-lg shadow-emerald-500/25 transition-all hover:scale-105 cursor-pointer"
            >
              <Play className="h-4 w-4 fill-slate-950" /> Start Workout
            </Link>

            <button
              type="button"
              onClick={() => setIsSaved(!isSaved)}
              className={`inline-flex items-center gap-1.5 rounded-xl border border-slate-800 px-4 py-2.5 text-xs font-semibold transition-colors cursor-pointer ${
                isSaved ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' : 'bg-slate-950 text-slate-300 hover:bg-slate-800'
              }`}
            >
              <Bookmark className="h-3.5 w-3.5" /> {isSaved ? 'Saved' : 'Save Workout'}
            </button>

            <button
              type="button"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-300 transition-colors cursor-pointer"
            >
              <Share2 className="h-3.5 w-3.5" /> Share
            </button>

            <button
              type="button"
              className="rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800 p-2.5 text-slate-400 hover:text-slate-200 transition-colors"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Right Photo Column (5 cols) */}
        <div className="lg:col-span-5 relative aspect-[16/10] lg:aspect-auto h-full min-h-[220px] bg-slate-950 overflow-hidden">
          <img
            src={image}
            alt={title}
            className="w-full h-full object-cover opacity-90"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent lg:bg-gradient-to-r" />
        </div>

      </div>
    </div>
  )
}
