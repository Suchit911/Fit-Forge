import React from 'react'
import { Star, Play, Dumbbell, Wrench, Clock, TrendingUp } from 'lucide-react'

export interface ExerciseHeroCardProps {
  title: string
  rating: number
  reviewCount: number
  description: string
  muscles: string
  equipment: string
  difficulty: string
  type: string
  image: string
  onWatchVideoClick: () => void
}

export const ExerciseHeroCard: React.FC<ExerciseHeroCardProps> = ({
  title,
  rating,
  reviewCount,
  description,
  muscles,
  equipment,
  difficulty,
  type,
  image,
  onWatchVideoClick,
}) => {
  return (
    <div className="relative rounded-3xl border border-slate-800 bg-slate-900 overflow-hidden shadow-2xl text-left">
      <div className="grid grid-cols-1 lg:grid-cols-12 items-center">
        
        {/* Left Information Column (7 cols) */}
        <div className="lg:col-span-7 p-6 sm:p-8 space-y-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-extrabold text-slate-100 tracking-tight">{title}</h1>
            
            <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
              <span className="flex items-center gap-1 text-amber-400 font-bold">
                <Star className="h-4 w-4 fill-amber-400" /> {rating}
                <span className="text-slate-400 font-normal">({reviewCount.toLocaleString()} reviews)</span>
              </span>
              <span className="rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-bold uppercase">
                POPULAR
              </span>
              <span className="rounded-full bg-slate-800 text-slate-300 border border-slate-700 px-2.5 py-0.5 text-[10px] font-semibold">
                Compound
              </span>
            </div>
          </div>

          {/* Description */}
          <p className="text-xs text-slate-300 leading-relaxed max-w-xl font-normal">
            {description}
          </p>

          {/* 4 Horizontal Info Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <Dumbbell className="h-3 w-3 text-emerald-400" /> Muscles
              </span>
              <span className="font-bold text-slate-200 block truncate">{muscles}</span>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <Wrench className="h-3 w-3 text-cyan-400" /> Equipment
              </span>
              <span className="font-bold text-slate-200 block truncate">{equipment}</span>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3 text-amber-400" /> Difficulty
              </span>
              <span className="font-bold text-slate-200 block truncate">{difficulty}</span>
            </div>

            <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1">
              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                <TrendingUp className="h-3 w-3 text-purple-400" /> Type
              </span>
              <span className="font-bold text-slate-200 block truncate">{type}</span>
            </div>
          </div>
        </div>

        {/* Right Demonstration Image & Watch Video Button (5 cols) */}
        <div className="lg:col-span-5 relative aspect-[16/10] lg:aspect-auto h-full min-h-[220px] bg-slate-950 overflow-hidden">
          <img
            src={image}
            alt={title}
            className="w-full h-full object-cover opacity-90"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent lg:bg-gradient-to-r" />

          {/* Watch Video Glass Button Overlay */}
          <button
            type="button"
            onClick={onWatchVideoClick}
            className="absolute bottom-4 right-4 inline-flex items-center gap-2 rounded-2xl bg-slate-950/80 hover:bg-slate-950 border border-slate-700/80 px-4 py-2.5 text-xs font-extrabold text-slate-100 backdrop-blur-md transition-all shadow-xl hover:scale-105 cursor-pointer"
          >
            <Play className="h-3.5 w-3.5 fill-slate-100 text-slate-100" /> Watch Video
          </button>
        </div>

      </div>
    </div>
  )
}
