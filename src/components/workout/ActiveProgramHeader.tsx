import React from 'react'
import { Layers, Calendar, Dumbbell, Sparkles, CheckCircle2, Archive, LogOut } from 'lucide-react'
import type { ProgramResponse } from '../../types/program.ts'
import {
  calculateProgramCompletionPercentage,
  formatSplitType,
} from '../../utils/activeProgramOverview.ts'

export interface ActiveProgramHeaderProps {
  program: ProgramResponse
  onOpenHistory?: () => void
  onAbandon?: () => void
}

export const ActiveProgramHeader: React.FC<ActiveProgramHeaderProps> = ({
  program,
  onOpenHistory,
  onAbandon,
}) => {
  const completedCount = program.completedWorkouts?.length || 0
  const totalCount = program.totalPlannedWorkouts || 0
  const { percentage: completionPercentage } = calculateProgramCompletionPercentage(
    completedCount,
    totalCount
  )

  const splitLabel = formatSplitType(program.splitType)
  const currentWeek = program.currentWeek || 1
  const totalWeeks = program.totalWeeks || 1
  const currentDay = program.currentDay || 1
  const daysPerWeek = program.daysPerWeek || 1
  const planVersion = program.planVersion || 1
  const isCompleted = program.status === 'completed'
  const isAbandoned = program.status === 'abandoned'

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 sm:p-6 backdrop-blur-sm space-y-6 text-left">
      {/* Top Badges & Meta */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            {isCompleted ? (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-bold border bg-emerald-500/15 text-emerald-300 border-emerald-500/40 uppercase tracking-wider flex items-center gap-1.5">
                <CheckCircle2 className="h-3 w-3 text-emerald-400" aria-hidden="true" />
                <span>Program Completed</span>
              </span>
            ) : isAbandoned ? (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold border bg-slate-800 text-slate-400 border-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Archive className="h-3 w-3 text-slate-400" aria-hidden="true" />
                <span>Program Abandoned</span>
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-bold border bg-emerald-500/10 text-emerald-400 border-emerald-500/30 uppercase tracking-wider">
                Active Program
              </span>
            )}
            <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold border bg-slate-800 text-slate-300 border-slate-700">
              {splitLabel}
            </span>
            {onOpenHistory ? (
              <button
                type="button"
                onClick={onOpenHistory}
                aria-label={`View adaptation history, currently Plan Version v${planVersion}`}
                className="px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/20 hover:border-cyan-400/50 flex items-center gap-1.5 transition-colors cursor-pointer min-h-[32px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
              >
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                <span>Plan Version v{planVersion}</span>
              </button>
            ) : (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-mono font-semibold border bg-cyan-500/10 text-cyan-400 border-cyan-500/30 flex items-center gap-1.5">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                <span>Plan Version v{planVersion}</span>
              </span>
            )}
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-100 tracking-tight break-words">
            {program.title || 'Personalized Workout Program'}
          </h2>
        </div>

        {/* Current Position Highlights & Actions */}
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          {program.status === 'active' && onAbandon && (
            <button
              type="button"
              id="abandon-program-btn"
              onClick={onAbandon}
              aria-label="Abandon active program"
              className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-950/20 hover:bg-red-950/40 text-red-400 hover:text-red-300 px-3.5 py-2.5 text-xs font-semibold transition-colors cursor-pointer min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Abandon Program</span>
            </button>
          )}
          <div className="flex items-center gap-2.5 rounded-xl border border-slate-800 bg-slate-950/60 px-3.5 py-2 min-h-[44px]">
            <Calendar className="h-4 w-4 text-emerald-400 shrink-0" aria-hidden="true" />
            <div className="text-left">
              <span className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider">Current Week</span>
              <span className="text-xs font-bold text-slate-200">
                Week {currentWeek} of {totalWeeks}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2.5 rounded-xl border border-slate-800 bg-slate-950/60 px-3.5 py-2 min-h-[44px]">
            <Dumbbell className="h-4 w-4 text-emerald-400 shrink-0" aria-hidden="true" />
            <div className="text-left">
              <span className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider">Current Day</span>
              <span className="text-xs font-bold text-slate-200">
                Day {currentDay} of {daysPerWeek}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Program Progress Bar */}
      <div className="space-y-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
          <span className="font-semibold text-slate-300 flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-emerald-400 shrink-0" aria-hidden="true" />
            <span>Program Completion</span>
          </span>
          <span className="font-mono text-slate-400">
            <strong className="text-slate-100 font-bold">{completedCount}</strong> of{' '}
            <strong className="text-slate-100 font-bold">{totalCount}</strong> workouts completed ({completionPercentage}%)
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={completionPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Overall Program Progress"
          className="h-2.5 w-full rounded-full bg-slate-800 overflow-hidden"
        >
          <div
            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full transition-all duration-500 ease-out shadow-sm shadow-emerald-500/20"
            style={{ width: `${completionPercentage}%` }}
          />
        </div>
      </div>
    </div>
  )
}
