import React from 'react'
import { CheckCircle2, Play, Clock, Moon, Layers, Sparkles } from 'lucide-react'

export type ProgramDayState = 'COMPLETED' | 'CURRENT' | 'UPCOMING' | 'REST'

export interface ProgramDayCardProps {
  dayNumber: number
  dayLabel: string
  focus?: string
  state: ProgramDayState
  totalSets?: number
  durationMinutes?: number
  isAdapted?: boolean
  isSelected?: boolean
  onSelect?: () => void
}

export const ProgramDayCard: React.FC<ProgramDayCardProps> = ({
  dayNumber,
  dayLabel,
  focus,
  state,
  totalSets = 0,
  durationMinutes = 45,
  isAdapted = false,
  isSelected = false,
  onSelect,
}) => {
  const isCurrent = state === 'CURRENT'
  const isCompleted = state === 'COMPLETED'
  const isRest = state === 'REST'
  const isUpcoming = state === 'UPCOMING'

  // Card background and border styles by state
  const stateStyles = {
    CURRENT: isSelected
      ? 'border-emerald-400 bg-emerald-950/40 shadow-lg shadow-emerald-500/10 ring-2 ring-emerald-500/50'
      : 'border-emerald-500/80 bg-emerald-950/20 hover:border-emerald-400 hover:bg-emerald-950/30',
    COMPLETED: isSelected
      ? 'border-slate-700 bg-slate-900/90 ring-2 ring-slate-600'
      : 'border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900/80',
    UPCOMING: isSelected
      ? 'border-slate-700 bg-slate-900/90 ring-2 ring-slate-600'
      : 'border-slate-800/80 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60',
    REST: isSelected
      ? 'border-slate-800 bg-slate-950/80 ring-2 ring-slate-700'
      : 'border-slate-800/60 bg-slate-950/40 hover:border-slate-800 hover:bg-slate-950/60',
  }[state]

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={isCurrent ? 'date' : undefined}
      aria-pressed={isSelected}
      aria-label={`Day ${dayNumber}: ${dayLabel}, ${state} status`}
      className={`w-full rounded-2xl border p-4 text-left transition-all cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 relative overflow-hidden flex flex-col justify-between min-h-[140px] ${stateStyles}`}
    >
      {/* Top Header: Day Number + State Badge */}
      <div className="flex items-center justify-between gap-2 w-full">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono font-bold text-slate-400 uppercase tracking-wider">
            Day {dayNumber}
          </span>
          {isAdapted && (
            <span
              title="Prescription adapted from baseline"
              className="inline-flex items-center gap-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-1.5 py-0.5 text-[9px] font-bold"
            >
              <Sparkles className="h-2.5 w-2.5" aria-hidden="true" /> Adapted
            </span>
          )}
        </div>

        {/* State Badge */}
        {isCurrent && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500 text-slate-950 px-2.5 py-0.5 text-[10px] font-extrabold shadow-sm shadow-emerald-500/30 tracking-wider uppercase">
            <Play className="h-2.5 w-2.5 fill-slate-950" aria-hidden="true" /> Today
          </span>
        )}
        {isCompleted && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-2.5 py-0.5 text-[10px] font-bold tracking-wide uppercase">
            <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> Done
          </span>
        )}
        {isUpcoming && (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
            Upcoming
          </span>
        )}
        {isRest && (
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase">
            <Moon className="h-2.5 w-2.5 text-slate-400" aria-hidden="true" /> Rest
          </span>
        )}
      </div>

      {/* Center: Workout Title & Focus */}
      <div className="my-2.5 space-y-1">
        <h4 className={`text-sm font-bold tracking-tight break-words ${isCurrent ? 'text-emerald-200' : 'text-slate-100'}`}>
          {dayLabel}
        </h4>
        {focus && (
          <p className="text-[11px] text-slate-400 break-words leading-relaxed">
            {focus}
          </p>
        )}
      </div>

      {/* Bottom Metadata: Sets & Duration */}
      <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800/60 w-full">
        {isRest ? (
          <span className="text-slate-400">Recovery Day</span>
        ) : (
          <>
            <span className="flex items-center gap-1">
              <Layers className="h-3 w-3 text-slate-400" aria-hidden="true" />
              <span>{totalSets} sets</span>
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3 text-slate-400" aria-hidden="true" />
              <span>~{durationMinutes} min</span>
            </span>
          </>
        )}
      </div>
    </button>
  )
}
