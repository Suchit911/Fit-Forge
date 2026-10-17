import React, { useState } from 'react'
import {
  Pause,
  Play,
  Maximize2,
  Check,
  Info,
  Dumbbell,
  Clock,
  Layers,
  ChevronLeft,
  ChevronRight,
  Activity,
  Gauge,
} from 'lucide-react'

export interface ActiveExerciseCardProps {
  currentExerciseIndex: number
  totalExercises: number
  exerciseName: string
  targetMuscle: string
  setsCount: number
  repRange: string
  restSeconds: number
  equipment: string
  formScore: number
  image: string
  slotRole?: string
  targetRpe?: number | null
  prescriptionRationale?: string | null
  recommendationReasons?: string[]
  movementPattern?: string
  onPreviousExercise?: () => void
  onNextExercise?: () => void
  hasPreviousExercise?: boolean
  hasNextExercise?: boolean
}

export const ActiveExerciseCard: React.FC<ActiveExerciseCardProps> = ({
  currentExerciseIndex,
  totalExercises,
  exerciseName,
  targetMuscle,
  setsCount,
  repRange,
  restSeconds,
  equipment,
  formScore,
  image,
  slotRole,
  targetRpe,
  prescriptionRationale,
  recommendationReasons,
  movementPattern,
  onPreviousExercise,
  onNextExercise,
  hasPreviousExercise,
  hasNextExercise,
}) => {
  const [isPlaying, setIsPlaying] = useState(true)

  const formattedRole = slotRole
    ? slotRole.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    : null

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6 space-y-4 text-left shadow-2xl relative">
      
      {/* Top Header Row & Form Score & Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="space-y-1 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-emerald-400">
              Exercise {currentExerciseIndex} of {totalExercises}
            </span>
            {formattedRole && (
              <span className="rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-wider">
                {formattedRole}
              </span>
            )}
            {movementPattern && (
              <span className="rounded-md bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider">
                {movementPattern.replace(/_/g, ' ')}
              </span>
            )}
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
            {exerciseName}
          </h2>
          <p className="text-xs font-semibold text-slate-400 capitalize">{targetMuscle}</p>

          {/* Metadata Specs Pills */}
          <div className="flex flex-wrap items-center gap-2 pt-2 text-xs font-mono">
            <span className="flex items-center gap-1 rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-1 text-slate-300">
              <Layers className="h-3.5 w-3.5 text-emerald-400" /> {setsCount} Sets
            </span>
            <span className="flex items-center gap-1 rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-1 text-slate-300">
              <Dumbbell className="h-3.5 w-3.5 text-emerald-400" /> {repRange} Reps
            </span>
            <span className="flex items-center gap-1 rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-1 text-slate-300">
              <Clock className="h-3.5 w-3.5 text-emerald-400" /> {restSeconds} sec Rest
            </span>
            {targetRpe && (
              <span className="flex items-center gap-1 rounded-lg bg-slate-950 border border-amber-500/30 px-2.5 py-1 text-amber-300">
                <Gauge className="h-3.5 w-3.5 text-amber-400" /> Target RPE {targetRpe}
              </span>
            )}
            <span className="flex items-center gap-1 rounded-lg bg-slate-950 border border-slate-800 px-2.5 py-1 text-slate-300 capitalize">
              {equipment}
            </span>
          </div>

          {/* Prescription Rationale & Reasons Callout */}
          {(prescriptionRationale || (recommendationReasons && recommendationReasons.length > 0)) && (
            <div className="pt-2 text-xs text-slate-300 space-y-1">
              {prescriptionRationale && (
                <div className="flex items-start gap-1.5 text-slate-300">
                  <Activity className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-slate-200">Prescription:</strong> {prescriptionRationale}
                  </span>
                </div>
              )}
              {recommendationReasons && recommendationReasons.length > 0 && (
                <div className="flex items-start gap-1.5 text-slate-400">
                  <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5" />
                  <span>
                    <strong className="text-slate-300">Why Selected:</strong>{' '}
                    {recommendationReasons.join(' • ')}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Top: Navigation Controls & Form Score */}
        <div className="flex sm:flex-col items-center justify-between gap-3">
          {/* Exercise Step Controls */}
          {(hasPreviousExercise !== undefined || hasNextExercise !== undefined) && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onPreviousExercise}
                disabled={!hasPreviousExercise}
                className="rounded-xl bg-slate-950 border border-slate-800 p-2 text-slate-300 hover:text-emerald-400 hover:border-slate-700 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
                aria-label="Previous Exercise"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={onNextExercise}
                disabled={!hasNextExercise}
                className="rounded-xl bg-slate-950 border border-slate-800 p-2 text-slate-300 hover:text-emerald-400 hover:border-slate-700 disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
                aria-label="Next Exercise"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}

        {/* Form Score Ring Top Right */}
        <div className="flex flex-col items-center text-center">
          <div className="flex items-center gap-1 text-[10px] text-slate-400 font-mono">
            <span>Form Score</span>
            <Info className="h-3 w-3 text-slate-500" />
          </div>
          <div className="relative flex items-center justify-center my-1">
            <svg className="h-16 w-16 transform -rotate-90">
              <circle cx="32" cy="32" r="26" stroke="#1e293b" strokeWidth="5" fill="transparent" />
              <circle
                cx="32"
                cy="32"
                r="26"
                stroke="#10b981"
                strokeWidth="5"
                strokeDasharray="163"
                strokeDashoffset="13"
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <span className="absolute text-sm font-extrabold text-slate-100 font-mono">
              {formScore}%
            </span>
          </div>
          <span className="text-[10px] font-bold text-emerald-400 font-mono">Great Form!</span>
        </div>
      </div>
    </div>

      {/* Main Exercise Video Demonstration Area */}
      <div className="relative aspect-[16/9] w-full rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 group">
        <img
          src={image}
          alt={exerciseName}
          className="w-full h-full object-cover opacity-85"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950/90 via-transparent to-slate-950/40" />

        {/* Expand Control Top Right */}
        <button
          type="button"
          aria-label="Expand video"
          className="absolute top-3 right-3 rounded-full bg-slate-950/60 p-2 text-slate-300 backdrop-blur-sm hover:text-emerald-400 transition-colors"
        >
          <Maximize2 className="h-4 w-4" />
        </button>

        {/* Center Play/Pause Button */}
        <button
          type="button"
          onClick={() => setIsPlaying(!isPlaying)}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex h-14 w-14 items-center justify-center rounded-full bg-slate-950/80 border border-slate-700 text-slate-100 shadow-2xl backdrop-blur-md hover:scale-110 transition-transform cursor-pointer"
        >
          {isPlaying ? (
            <Pause className="h-6 w-6 fill-slate-100" />
          ) : (
            <Play className="h-6 w-6 fill-slate-100 ml-0.5" />
          )}
        </button>

        {/* Bottom AI Feedback Overlay & Progress Line */}
        <div className="absolute bottom-3 left-3 right-3 space-y-2 text-left">
          <div className="flex items-center gap-2 rounded-xl bg-slate-950/80 border border-emerald-500/30 px-3 py-2 backdrop-blur-md text-xs font-medium text-slate-200">
            <Check className="h-4 w-4 text-emerald-400 shrink-0" />
            <span>Keep your feet flat and maintain shoulder blade retraction</span>
          </div>

          {/* Video Timeline Progress */}
          <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
            <span>00:15</span>
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: '33%' }} />
            </div>
            <span>00:45</span>
          </div>
        </div>
      </div>

    </div>
  )
}
