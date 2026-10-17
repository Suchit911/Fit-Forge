import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, Moon, Play, Info } from 'lucide-react'
import { useEffectivePrescription } from '../../hooks/useActiveProgram.ts'
import { Skeleton } from '../ui/Skeleton.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { getSlotRoleMeta } from '../../utils/activeProgramOverview.ts'
import {
  workoutPlanExecutionService,
  type GeneratedWorkoutExecutionContext,
} from '../../services/workoutPlanExecutionService.ts'
import type { ProgramResponse } from '../../types/program.ts'
import { AdaptationStatusCard } from './AdaptationStatusCard.tsx'

export interface TodayPrescriptionPreviewProps {
  week: number
  day: number
  isToday: boolean
  isRestDay?: boolean
  dayLabel?: string
  program?: ProgramResponse | null
  onOpenHistory?: () => void
}

export const TodayPrescriptionPreview: React.FC<TodayPrescriptionPreviewProps> = ({
  week,
  day,
  isToday,
  isRestDay = false,
  dayLabel = `Day ${day}`,
  program,
  onOpenHistory,
}) => {
  const navigate = useNavigate()
  // Authoritative prescription query (unconditional hook call respecting React Rules of Hooks)
  const { prescription, isLoading, isError, error, refetch } = useEffectivePrescription(week, day, {
    enabled: !isRestDay && week >= 1 && day >= 1,
  })

  // If it's a planned rest day, render rest day view without querying prescription
  if (isRestDay) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 text-center space-y-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800/80 text-slate-400 border border-slate-700">
          <Moon className="h-6 w-6" />
        </div>
        <div className="space-y-1">
          <h3 className="text-lg font-bold text-slate-200">Scheduled Rest & Recovery</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Week {week}, {dayLabel} is designated for recovery. Rest periods allow muscular repair, glycogen replenishment, and central nervous system adaptation.
          </p>
        </div>
        <div className="pt-2">
          <span className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950 px-4 py-2 text-xs font-mono text-slate-400">
            <Info className="h-3.5 w-3.5 text-slate-400" /> No training scheduled today
          </span>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 space-y-6 text-left">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-72" />
          </div>
          <Skeleton className="h-9 w-32 rounded-xl" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-16 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError || !prescription) {
    return (
      <ErrorState
        title="Failed to Load Prescription"
        message={
          error?.message ||
          `Unable to retrieve the authoritative workout prescription for Week ${week}, Day ${day}.`
        }
        onRetry={() => refetch()}
      />
    )
  }

  const plannedDay = prescription.day
  const exercises = plannedDay?.exercises || []
  const workoutTitle = plannedDay?.day_label || plannedDay?.dayLabel || dayLabel
  const focus = plannedDay?.focus || 'General Training Focus'
  const isAdapted = prescription.isAdapted || prescription.is_adapted || false
  const phaseLabel = prescription.phaseLabel || prescription.phase_label || ''

  const handleStartWorkout = () => {
    if (!prescription || !prescription.day || isRestDay || program?.status !== 'active') return

    // Program execution requires all four coordinates: programId, planId, weekNumber, dayNumber
    if (
      !prescription.programId ||
      !prescription.planId ||
      typeof prescription.weekNumber !== 'number' ||
      prescription.weekNumber < 1 ||
      typeof prescription.dayNumber !== 'number' ||
      prescription.dayNumber < 1
    ) {
      console.error('Cannot launch program workout: missing or invalid program coordinates', prescription)
      return
    }

    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: program?.title || 'Personalized Workout Program',
      splitType: program?.splitType || 'upper_lower',
      weekNumber: prescription.weekNumber,
      dayNumber: prescription.dayNumber,
      phaseLabel: prescription.phaseLabel || (isAdapted ? 'Adapted Prescription' : 'Program Workout'),
      day: prescription.day,
      isAdapted: isAdapted,
      baseWorkoutId: workoutPlanExecutionService.resolveBaseWorkoutId(prescription.day, program?.splitType),
    }

    const validation = workoutPlanExecutionService.validateExecutionContext(context)
    if (!validation.isValid) {
      console.error('Cannot launch program workout: validation failed', validation.error)
      return
    }

    workoutPlanExecutionService.setActiveExecutionContext(context)
    navigate('/workouts/generated/active', { state: context })
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 sm:p-8 backdrop-blur-sm space-y-6 text-left">
      {/* Header: Title, Phase, Adaptation Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            {isToday && (
              <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold bg-emerald-500 text-slate-950 uppercase tracking-wider">
                Today's Workout
              </span>
            )}
            <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold border bg-slate-800 text-slate-300 border-slate-700">
              Week {week} • Day {day}
            </span>
            {phaseLabel && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-semibold border bg-slate-800/80 text-slate-400 border-slate-700">
                {phaseLabel}
              </span>
            )}
            {isAdapted && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold border bg-cyan-500/10 text-cyan-400 border-cyan-500/30 flex items-center gap-1">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                <span>Adapted Prescription</span>
              </span>
            )}
          </div>
          <h3 className="text-xl sm:text-2xl font-black text-slate-100 tracking-tight break-words">
            {workoutTitle}
          </h3>
          <p className="text-xs text-slate-400 mt-1 break-words leading-relaxed">{focus}</p>
        </div>

        {/* Execution Start Button or Read-Only Status */}
        <div className="flex items-center gap-2 shrink-0">
          {program?.status === 'completed' ? (
            <span className="px-3 py-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs font-semibold">
              Program Completed (Read-Only)
            </span>
          ) : program?.status === 'abandoned' ? (
            <span className="px-3 py-2 rounded-xl border border-slate-700 bg-slate-800 text-slate-400 text-xs font-semibold">
              Program Abandoned (Read-Only)
            </span>
          ) : program?.status === 'active' && !isRestDay ? (
            <button
              type="button"
              id="start-program-workout-btn"
              onClick={handleStartWorkout}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-bold px-4 py-2.5 text-xs shadow-lg shadow-emerald-500/20 transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <Play className="h-3.5 w-3.5 fill-slate-950 text-slate-950" aria-hidden="true" />
              <span>{isToday ? "Start Today's Workout" : "Start Workout"}</span>
            </button>
          ) : null}
        </div>
      </div>

      {/* Authoritative Adaptation Status Presentation Area */}
      <AdaptationStatusCard
        prescription={prescription}
        program={program}
        week={week}
        day={day}
        onOpenHistory={onOpenHistory}
      />

      {/* Prescription Exercise List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-xs text-slate-400 font-mono border-b border-slate-800/60 pb-2">
          <span>Authoritative Prescribed Exercises ({exercises.length})</span>
          <span>Target Sets & Reps</span>
        </div>

        {exercises.map((ex, idx) => {
          const slotRole = ex.slot_role || ex.slotRole || 'primary_compound'
          const roleBadge = getSlotRoleMeta(slotRole)

          const firstSet = ex.prescribed_sets?.[0] || {}
          const repsDisplay =
            firstSet.target_reps_min && firstSet.target_reps_max
              ? `${firstSet.target_reps_min}–${firstSet.target_reps_max}`
              : `${firstSet.target_reps || 10}`

          const restDisplay = `${firstSet.rest_seconds || 90}s rest`
          const rpeDisplay = firstSet.target_rpe ? `@ RPE ${firstSet.target_rpe}` : null
          const weightDisplay = firstSet.weight_kg ? `@ ${firstSet.weight_kg} kg` : null
          const isExAdapted = ex.is_adapted || ex.isAdapted || false

          return (
            <div
              key={ex.exercise_id || idx}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-slate-700 transition-colors text-left"
            >
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 border border-slate-800 text-emerald-400 shrink-0 font-mono text-xs font-bold mt-0.5" aria-hidden="true">
                  {idx + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h4 className="text-sm font-bold text-slate-100 break-words">{ex.name}</h4>
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[9px] font-semibold ${roleBadge.badgeClass}`}
                    >
                      {roleBadge.label}
                    </span>
                    {isExAdapted && (
                      <span className="inline-flex items-center gap-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-1.5 py-0.5 text-[9px] font-bold">
                        <Sparkles className="h-2 w-2" aria-hidden="true" /> Adapted
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5 flex flex-wrap items-center gap-2">
                    <span className="capitalize">{ex.primary_muscles?.join(', ') || 'Full Body'}</span>
                    <span aria-hidden="true">•</span>
                    <span className="capitalize">{ex.equipment?.join(', ') || 'Bodyweight'}</span>
                  </p>
                  {ex.prescription_rationale && (
                    <p className="text-[10px] text-slate-400 mt-1 italic break-words">
                      {ex.prescription_rationale}
                    </p>
                  )}
                </div>
              </div>

              {/* Set / Rep / Weight Prescription Badges */}
              <div className="flex flex-wrap sm:flex-col items-start sm:items-end gap-1.5 shrink-0 pl-12 sm:pl-0">
                <span className="text-xs font-mono font-bold text-slate-200">
                  {ex.total_sets || ex.prescribed_sets?.length || 3} sets × {repsDisplay} reps
                </span>
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-400">
                  {weightDisplay && <span className="text-cyan-300 font-bold">{weightDisplay}</span>}
                  {rpeDisplay && <span>{rpeDisplay}</span>}
                  <span>{restDisplay}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
