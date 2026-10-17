import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Play, Dumbbell, Clock, Layers, Calendar, Sparkles, Moon } from 'lucide-react'
import { useActiveProgram, useEffectivePrescription } from '../../hooks/useActiveProgram.ts'
import { Skeleton } from '../ui/Skeleton.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import {
  workoutPlanExecutionService,
  type GeneratedWorkoutExecutionContext,
} from '../../services/workoutPlanExecutionService.ts'

export const TodayWorkoutCard: React.FC = () => {
  const navigate = useNavigate()

  // 1. Authoritative active program query
  const {
    program,
    hasActiveProgram,
    isLoading: isProgramLoading,
    isError: isProgramError,
    error: programError,
    refetch: refetchProgram,
  } = useActiveProgram()

  const currentWeek = program?.currentWeek || 1
  const currentDay = program?.currentDay || 1
  const isProgramActive = !!program && program.status === 'active'

  // 2. Authoritative effective prescription query for active program week/day
  const {
    prescription,
    isLoading: isPrescriptionLoading,
    isError: isPrescriptionError,
    error: prescriptionError,
    refetch: refetchPrescription,
  } = useEffectivePrescription(currentWeek, currentDay, {
    enabled: isProgramActive,
  })

  // Loading State
  if (isProgramLoading || (isProgramActive && isPrescriptionLoading)) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <Skeleton className="h-5 w-36" />
          <Skeleton className="h-4 w-20" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          <div className="md:col-span-7">
            <Skeleton className="aspect-[16/9] w-full rounded-xl" />
          </div>
          <div className="md:col-span-5 space-y-2.5">
            <Skeleton className="h-12 w-full rounded-xl" />
            <Skeleton className="h-12 w-full rounded-xl" />
            <Skeleton className="h-12 w-full rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  // Program API Error State
  if (isProgramError) {
    return (
      <ErrorState
        title="Failed to Load Active Program"
        message={programError?.message || 'Could not retrieve your active workout program.'}
        onRetry={() => refetchProgram()}
      />
    )
  }

  // Empty State: No active program
  if (!hasActiveProgram || !program || program.status !== 'active') {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-left space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" /> Today's Workout
          </h3>
          <Link
            to="/workouts"
            className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
          >
            Browse Library
          </Link>
        </div>

        <div className="py-6 flex flex-col items-center justify-center text-center space-y-3">
          <div className="h-12 w-12 rounded-full bg-slate-800/60 flex items-center justify-center text-slate-400">
            <Dumbbell className="h-6 w-6" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-slate-200">No Active Workout Program</h4>
            <p className="text-xs text-slate-400 max-w-sm">
              Generate a personalized workout plan or browse workouts from your library to start your mesocycle.
            </p>
          </div>
          <div className="flex gap-3 pt-2">
            <Link
              to="/workouts?tab=generate"
              className="inline-flex items-center justify-center rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-4 py-2 text-xs font-bold transition-all shadow-md shadow-emerald-500/20"
            >
              Generate Plan
            </Link>
            <Link
              to="/workouts"
              className="inline-flex items-center justify-center rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 transition-colors"
            >
              Browse Workouts
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Prescription API Error State
  if (isPrescriptionError) {
    return (
      <ErrorState
        title="Failed to Load Prescription"
        message={
          prescriptionError?.message ||
          `Unable to retrieve the workout prescription for Week ${currentWeek}, Day ${currentDay}.`
        }
        onRetry={() => refetchPrescription()}
      />
    )
  }

  // Scheduled Rest Day or Missing Prescription Day
  const plannedDay = prescription?.day
  const exercises = plannedDay?.exercises || []
  const isRestDay = !plannedDay || exercises.length === 0

  if (isRestDay) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/40 p-6 text-left space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <h3 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
            <Calendar className="h-4 w-4 text-emerald-400" /> Today's Workout
          </h3>
          <Link
            to="/workouts"
            className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
          >
            View Program
          </Link>
        </div>

        <div className="py-6 flex flex-col items-center justify-center text-center space-y-3">
          <div className="h-12 w-12 rounded-full bg-slate-800/60 flex items-center justify-center text-slate-400">
            <Moon className="h-6 w-6 text-cyan-400" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-slate-200">Scheduled Rest & Recovery</h4>
            <p className="text-xs text-slate-400 max-w-sm">
              Week {currentWeek}, Day {currentDay} is designated for recovery. Rest allows muscular repair and adaptation.
            </p>
          </div>
          <div className="flex gap-3 pt-2">
            <Link
              to="/workouts"
              className="inline-flex items-center justify-center rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-4 py-2 text-xs font-bold transition-all shadow-md shadow-emerald-500/20"
            >
              View Mesocycle
            </Link>
            <Link
              to="/workouts"
              className="inline-flex items-center justify-center rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-200 transition-colors"
            >
              Browse Library
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Active Prescription Presentation
  const workoutTitle = plannedDay.day_label || plannedDay.dayLabel || `Week ${currentWeek} • Day ${currentDay}`
  const focus = plannedDay.focus || 'Prescribed mesocycle workout'
  const isAdapted = prescription.isAdapted || prescription.is_adapted || false
  const phaseLabel = prescription.phaseLabel || prescription.phase_label || program.title

  const exerciseDetails = exercises.map((ex) => {
    const firstSet = ex.prescribed_sets?.[0]
    const repsDisplay =
      firstSet?.target_reps_min && firstSet?.target_reps_max
        ? `${firstSet.target_reps_min}–${firstSet.target_reps_max}`
        : `${firstSet?.target_reps || 10}`
    const setsCount = ex.total_sets || ex.prescribed_sets?.length || 3
    return {
      name: ex.name,
      sets: `${setsCount} sets × ${repsDisplay} reps`,
      weight: firstSet?.weight_kg ? `${firstSet.weight_kg} kg` : null,
      rpe: firstSet?.target_rpe ? `RPE ${firstSet.target_rpe}` : null,
      isAdapted: ex.is_adapted || ex.isAdapted || false,
    }
  })

  const handleStartWorkout = () => {
    if (!prescription || !prescription.day || program.status !== 'active') return

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
      planTitle: program.title || 'Personalized Workout Program',
      splitType: program.splitType || 'upper_lower',
      weekNumber: prescription.weekNumber,
      dayNumber: prescription.dayNumber,
      phaseLabel: prescription.phaseLabel || (isAdapted ? 'Adapted Prescription' : 'Program Workout'),
      day: prescription.day,
      isAdapted: isAdapted,
      baseWorkoutId: workoutPlanExecutionService.resolveBaseWorkoutId(prescription.day, program.splitType),
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
    <div className="rounded-2xl border border-slate-800 bg-slate-900/90 p-5 text-left space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <h3 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-emerald-400" /> Today's Workout
        </h3>
        <Link
          to="/workouts"
          className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
        >
          See Program
        </Link>
      </div>

      {/* Main Grid: Left Visual Banner + Right Exercise Checklist */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
        {/* Left Image & Action Card Column */}
        <div className="md:col-span-7 space-y-4">
          <div className="relative aspect-[16/9] w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800">
            <img
              src="/assets/dashboard_push_lifter.jpg"
              alt={`${workoutTitle} lifter`}
              className="w-full h-full object-cover opacity-85"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent" />

            <div className="absolute top-3 left-3 flex flex-wrap items-center gap-1.5">
              <span className="rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider">
                Week {currentWeek} • Day {currentDay}
              </span>
              {isAdapted && (
                <span className="rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
                  <Sparkles className="h-2.5 w-2.5" /> Adapted
                </span>
              )}
            </div>

            <div className="absolute bottom-3 left-3 right-3 text-left">
              <h4 className="text-base sm:text-lg font-extrabold text-slate-100 tracking-tight">
                {workoutTitle}
              </h4>
              <p className="text-xs text-slate-300 line-clamp-1 mt-0.5">{focus}</p>
              <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-300 font-mono">
                <span className="flex items-center gap-1">
                  <Layers className="h-3 w-3 text-emerald-400" /> {exercises.length} Exercises
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3 text-emerald-400" /> ~45 min
                </span>
                <span className="flex items-center gap-1">
                  <Dumbbell className="h-3 w-3 text-emerald-400" /> {phaseLabel}
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              id="start-today-workout-btn"
              onClick={handleStartWorkout}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 py-2.5 text-xs font-extrabold shadow-md shadow-emerald-500/20 transition-all cursor-pointer min-h-[44px]"
            >
              <Play className="h-3.5 w-3.5 fill-slate-950" /> Start Workout
            </button>
            <Link
              to="/workouts"
              className="inline-flex items-center justify-center rounded-xl border border-slate-800 bg-slate-950 hover:bg-slate-800 px-4 py-2.5 text-xs font-semibold text-slate-200 transition-colors min-h-[44px]"
            >
              View Program
            </Link>
          </div>
        </div>

        {/* Right Exercise List Column */}
        <div className="md:col-span-5 space-y-2.5">
          {exerciseDetails.slice(0, 5).map((ex, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center gap-2.5 min-w-0 flex-1">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 border border-slate-800 text-emerald-400 shrink-0 font-mono text-xs font-bold">
                  {idx + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <h5 className="text-xs font-bold text-slate-100 truncate">{ex.name}</h5>
                    {ex.isAdapted && (
                      <span className="text-[9px] font-mono text-cyan-400 font-bold shrink-0">
                        *Adapted
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono block">
                    {ex.sets} {ex.weight ? `• ${ex.weight}` : ''}
                  </span>
                </div>
              </div>
            </div>
          ))}
          {exerciseDetails.length > 5 && (
            <p className="text-[10px] text-slate-500 font-mono text-center pt-1">
              +{exerciseDetails.length - 5} more exercises in prescription
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
