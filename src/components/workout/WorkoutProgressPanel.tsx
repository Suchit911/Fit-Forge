import React, { useState, useEffect } from 'react'
import { Pause, Play, Square } from 'lucide-react'

export interface WorkoutProgressPanelProps {
  onEndWorkoutClick: () => void
}

export const WorkoutProgressPanel: React.FC<WorkoutProgressPanelProps> = ({ onEndWorkoutClick }) => {
  const [elapsedSeconds, setElapsedSeconds] = useState(1530) // 25:30
  const [isPaused, setIsPaused] = useState(false)

  useEffect(() => {
    if (!isPaused) {
      const timer = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1)
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [isPaused])

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const progressPercent = Math.min(Math.round((elapsedSeconds / 2700) * 100), 100)

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 text-left">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h3 className="text-xs font-mono font-extrabold text-slate-300 uppercase tracking-wider">
          Workout Progress
        </h3>
      </div>

      {/* Elapsed vs Total Time */}
      <div className="flex items-baseline justify-between font-mono">
        <div>
          <span className="text-3xl font-extrabold text-slate-100 tracking-tight block">
            {formatTime(elapsedSeconds)}
          </span>
          <span className="text-[10px] text-slate-400 uppercase">Elapsed Time</span>
        </div>

        <div className="text-right">
          <span className="text-lg font-bold text-slate-400 block">45:00</span>
          <span className="text-[10px] text-slate-500 uppercase">Total Duration</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
          <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${progressPercent}%` }} />
        </div>
        <span className="text-[10px] font-mono text-emerald-400 float-right font-bold">{progressPercent}%</span>
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-3 pt-2">
        <button
          type="button"
          onClick={() => setIsPaused(!isPaused)}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800 py-2.5 text-xs font-bold text-slate-200 transition-colors cursor-pointer"
        >
          {isPaused ? (
            <>
              <Play className="h-3.5 w-3.5 fill-slate-200" /> Resume Workout
            </>
          ) : (
            <>
              <Pause className="h-3.5 w-3.5" /> Pause Workout
            </>
          )}
        </button>

        <button
          type="button"
          onClick={onEndWorkoutClick}
          className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-red-500/30 bg-red-950/30 hover:bg-red-900/50 py-2.5 text-xs font-bold text-red-400 transition-colors cursor-pointer"
        >
          <Square className="h-3.5 w-3.5 fill-red-400" /> End Workout
        </button>
      </div>

    </div>
  )
}
