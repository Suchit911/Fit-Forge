import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Clock,
  Dumbbell,
  CheckCircle2,
  AlertCircle,
  Info,
  RefreshCw,
  Flame,
  Activity,
  Play,
  Sparkles,
  Loader2,
} from 'lucide-react'
import type {
  WorkoutPlanResponse,
  PlannedWeek,
  PlannedWorkoutDay,
  PlannedExercise,
  ExerciseSlotRole,
  DurationFeasibility,
} from '../../../types/workoutPlan'
import {
  workoutPlanExecutionService,
  type GeneratedWorkoutExecutionContext,
} from '../../../services/workoutPlanExecutionService'
import { useStartProgram } from '../../../hooks/useActiveProgram'
import { useToast } from '../../ui/Toast'

interface GeneratedWorkoutPlanViewProps {
  plan: WorkoutPlanResponse
  onReconfigure: () => void
  onStartWorkout?: (context: GeneratedWorkoutExecutionContext) => void
}

const SLOT_ROLE_LABELS: Record<ExerciseSlotRole, { label: string; badgeClass: string }> = {
  warmup_corrective: {
    label: 'Warm-up / Corrective',
    badgeClass: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
  },
  primary_compound: {
    label: 'Primary Compound',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 font-bold',
  },
  secondary_compound: {
    label: 'Secondary Compound',
    badgeClass: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  },
  accessory_1: {
    label: 'Accessory 1',
    badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
  },
  accessory_2: {
    label: 'Accessory 2',
    badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
  },
  core_mobility: {
    label: 'Core / Mobility',
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  },
}

const FEASIBILITY_MAP: Record<
  DurationFeasibility,
  { label: string; badgeClass: string; icon: typeof CheckCircle2; note: string }
> = {
  feasible: {
    label: 'Fits Target',
    badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    icon: CheckCircle2,
    note: 'Workout duration aligns with your configured target session duration.',
  },
  potentially_over_target: {
    label: 'May Run Over Target',
    badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    icon: AlertCircle,
    note: 'Duration estimate may exceed target by a small margin due to prescribed rest and setup times.',
  },
  impossible_under_constraints: {
    label: 'Cannot Fit Target as Configured',
    badgeClass: 'bg-red-500/10 text-red-400 border-red-500/30',
    icon: AlertCircle,
    note: 'Prescribed sets and rest periods exceed the target duration under these movement constraints.',
  },
}

const SPLIT_LABELS: Record<string, string> = {
  full_body: 'Full Body Split',
  upper_lower: 'Upper / Lower Split',
  push_pull_legs: 'Push / Pull / Legs Split',
}

export const GeneratedWorkoutPlanView: React.FC<GeneratedWorkoutPlanViewProps> = ({
  plan,
  onReconfigure,
  onStartWorkout,
}) => {
  const navigate = useNavigate()
  const { mutateAsync: startProgram, isPending: isStarting } = useStartProgram()
  const { showToast } = useToast()
  const [startError, setStartError] = useState<string | null>(null)
  const [selectedWeekIndex, setSelectedWeekIndex] = useState<number>(0)
  const [selectedDayIndex, setSelectedDayIndex] = useState<number>(0)

  const activeWeek: PlannedWeek | undefined = plan.weeks[selectedWeekIndex] || plan.weeks[0]
  const activeDay: PlannedWorkoutDay | undefined = activeWeek?.days[selectedDayIndex] || activeWeek?.days[0]

  const feasibility = FEASIBILITY_MAP[plan.duration_feasibility] || FEASIBILITY_MAP.feasible
  const FeasibilityIcon = feasibility.icon

  const handleStartActiveProgram = async () => {
    setStartError(null)
    try {
      await startProgram({
        plan,
        title: plan.title,
        createdFrom: 'generated_plan',
      })
      showToast('Active program started successfully!', 'success')
      navigate('/workouts?tab=program')
    } catch (err: any) {
      const errMsg = err?.message || 'Failed to start active program.'
      setStartError(errMsg)
      showToast(errMsg, 'error')
    }
  }

  const handleStartWorkout = () => {
    if (!activeDay || !activeWeek) return
    const context: GeneratedWorkoutExecutionContext = {
      planId: plan.plan_id,
      planTitle: plan.title,
      splitType: plan.split_type,
      weekNumber: activeWeek.week_number,
      phaseLabel: activeWeek.phase_label,
      day: activeDay,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    if (onStartWorkout) {
      onStartWorkout(context)
    } else {
      navigate('/workouts/generated/active', { state: context })
    }
  }

  return (
    <div className="space-y-6 text-left">
      {/* Program Header Card */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 sm:p-8 backdrop-blur-sm space-y-4">
        {/* Error Alert Banner if Start Program Fails */}
        {startError && (
          <div
            role="alert"
            className="rounded-xl border border-red-500/40 bg-red-500/10 p-4 text-xs text-red-300 flex items-start gap-3"
          >
            <AlertCircle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold text-red-200">Unable to Start Active Program</p>
              <p className="leading-relaxed">{startError}</p>
              {startError.toLowerCase().includes('already exists') && (
                <button
                  type="button"
                  onClick={() => navigate('/workouts?tab=program')}
                  className="mt-1 text-emerald-400 hover:text-emerald-300 underline font-semibold cursor-pointer inline-block"
                >
                  View current active program
                </button>
              )}
            </div>
          </div>
        )}

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold border bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                {SPLIT_LABELS[plan.split_type] || plan.split_type}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-slate-800 text-slate-300 border-slate-700">
                {plan.total_weeks} {plan.total_weeks === 1 ? 'Week' : 'Weeks'}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold border bg-slate-800 text-slate-300 border-slate-700">
                {plan.training_days_per_week} Days / Week
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border flex items-center gap-1 ${feasibility.badgeClass}`}
              >
                <FeasibilityIcon className="h-3 w-3" />
                <span>{feasibility.label}</span>
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-slate-100 tracking-tight">{plan.title}</h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-2xl leading-relaxed">{plan.description}</p>
          </div>

          <div className="flex flex-wrap items-center gap-3 shrink-0">
            <button
              type="button"
              id="start-active-program-btn"
              onClick={handleStartActiveProgram}
              disabled={isStarting}
              className="min-h-[44px] inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 px-4 py-2.5 text-xs font-extrabold shadow-lg shadow-emerald-500/25 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              {isStarting ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  <span>Starting Program...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>Start Active Program</span>
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onReconfigure}
              disabled={isStarting}
              className="min-h-[44px] inline-flex items-center justify-center gap-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 px-4 py-2.5 text-xs font-bold transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Reconfigure
            </button>
          </div>
        </div>

        {/* Diagnostic Plan ID & Feasibility Note */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-[11px] text-slate-500">
          <span className="font-mono">Plan ID: {plan.plan_id}</span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <Info className="h-3.5 w-3.5 text-slate-500 shrink-0" />
            <span>{feasibility.note}</span>
          </span>
        </div>
      </div>

      {/* Week Selector Tabs */}
      <div className="space-y-2">
        <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
          Select Program Week ({plan.weeks.length} Total)
        </label>
        <div role="tablist" aria-label="Program weeks" className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
          {plan.weeks.map((wk, idx) => {
            const isSelected = selectedWeekIndex === idx
            return (
              <button
                key={wk.week_number}
                role="tab"
                id={`plan-week-tab-${wk.week_number}`}
                aria-selected={isSelected}
                tabIndex={isSelected ? 0 : -1}
                type="button"
                onClick={() => {
                  setSelectedWeekIndex(idx)
                  setSelectedDayIndex(0)
                }}
                onKeyDown={(e) => {
                  let targetIdx = -1
                  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                    e.preventDefault()
                    targetIdx = (idx + 1) % plan.weeks.length
                  } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                    e.preventDefault()
                    targetIdx = (idx - 1 + plan.weeks.length) % plan.weeks.length
                  } else if (e.key === 'Home') {
                    e.preventDefault()
                    targetIdx = 0
                  } else if (e.key === 'End') {
                    e.preventDefault()
                    targetIdx = plan.weeks.length - 1
                  }
                  if (targetIdx !== -1) {
                    setSelectedWeekIndex(targetIdx)
                    setSelectedDayIndex(0)
                    document.getElementById(`plan-week-tab-${plan.weeks[targetIdx].week_number}`)?.focus()
                  }
                }}
                className={`min-h-[44px] px-4 py-3 rounded-xl border text-left transition-all cursor-pointer shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 ${isSelected
                    ? 'border-emerald-500 bg-emerald-500/10 text-slate-100 shadow-md shadow-emerald-500/10 font-bold'
                    : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-xs ${isSelected ? 'text-emerald-300' : 'text-slate-300'}`}>
                    Week {wk.week_number}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {wk.total_weekly_sets} sets
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5 truncate max-w-[140px]">
                  {wk.phase_label}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Day Selection Cards for Active Week (Button Group) */}
      {activeWeek && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
              Week {activeWeek.week_number} — {activeWeek.phase_label} Workouts
            </label>
            <span className="text-xs text-slate-500 font-mono">
              {activeWeek.total_workouts} Workouts • {activeWeek.total_weekly_sets} Weekly Sets
            </span>
          </div>

          <div role="group" aria-label={`Week ${activeWeek.week_number} workouts`} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {activeWeek.days.map((day, dIdx) => {
              const isSelected = selectedDayIndex === dIdx
              return (
                <button
                  key={day.day_number}
                  type="button"
                  aria-pressed={isSelected}
                  aria-label={`Day ${day.day_number}: ${day.day_label}`}
                  onClick={() => setSelectedDayIndex(dIdx)}
                  className={`min-h-[44px] p-4 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 ${isSelected
                      ? 'border-emerald-500 bg-emerald-500/10 text-slate-100 shadow-md shadow-emerald-500/10'
                      : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-extrabold ${isSelected ? 'text-emerald-300' : 'text-slate-200'}`}>
                        Day {day.day_number}: {day.day_label}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                        <Clock className="h-3 w-3" aria-hidden="true" />
                        {day.estimated_duration_minutes}m
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-1">{day.focus}</p>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 mt-3 pt-2 border-t border-slate-800/80">
                    <span>{day.exercises.length} Exercises</span>
                    <span>{day.total_sets} Sets</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Planned Exercises for Active Day */}
      {activeDay && (
        <div className="space-y-4 pt-2">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-base font-extrabold text-slate-100 flex items-center gap-2">
                <Dumbbell className="h-4 w-4 text-emerald-400" aria-hidden="true" />
                <span>{activeDay.day_label} Routine</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Focus: {activeDay.focus} • Estimated Session: ~{activeDay.estimated_duration_minutes} minutes • Week {activeWeek.week_number} ({activeWeek.phase_label})
              </p>
            </div>
            <div className="flex items-center gap-3 self-end sm:self-auto">
              <span className="text-xs font-mono font-bold text-emerald-400 hidden sm:inline">
                {activeDay.total_sets} Total Sets
              </span>
              <button
                type="button"
                id="start-generated-workout-btn"
                onClick={handleStartWorkout}
                className="min-h-[44px] inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 px-5 py-2.5 text-xs font-extrabold shadow-lg shadow-emerald-500/25 transition-all hover:scale-105 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
                aria-label={`Start Day ${activeDay.day_number}: ${activeDay.day_label} workout`}
              >
                <Play className="h-4 w-4 fill-slate-950" aria-hidden="true" />
                <span>Start Workout</span>
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {activeDay.exercises.map((ex: PlannedExercise) => {
              const roleMeta = SLOT_ROLE_LABELS[ex.slot_role] || {
                label: ex.slot_role,
                badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
              }

              return (
                <div
                  key={`${ex.exercise_id}_${ex.slot_index}`}
                  className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 sm:p-6 space-y-4 hover:border-slate-700 transition-colors"
                >
                  {/* Top exercise row */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider border ${roleMeta.badgeClass}`}>
                          {roleMeta.label}
                        </span>
                        <span className="px-2 py-0.5 rounded-md text-[10px] uppercase font-mono tracking-wider border border-slate-700 bg-slate-800 text-slate-300">
                          {ex.movement_pattern}
                        </span>
                        {ex.is_canonical_cv && (
                          <span className="px-2 py-0.5 rounded-md text-[10px] uppercase font-mono tracking-wider border border-cyan-500/30 bg-cyan-500/10 text-cyan-400">
                            CV Tracked
                          </span>
                        )}
                      </div>
                      <h4 className="text-base font-bold text-slate-100">{ex.name}</h4>
                    </div>

                    <div className="flex items-center gap-3 text-xs font-mono text-slate-400">
                      <span className="flex items-center gap-1">
                        <Flame className="h-3.5 w-3.5 text-amber-400" aria-hidden="true" />
                        {ex.total_sets} Sets
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
                        ~{ex.estimated_duration_minutes} min
                      </span>
                    </div>
                  </div>

                  {/* Prescribed Sets Table */}
                  <div className="overflow-x-auto max-w-full">
                    <table className="w-full min-w-[440px] text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800/80 text-[10px] uppercase tracking-wider font-mono text-slate-400">
                          <th className="py-2 pr-4">Set</th>
                          <th className="py-2 pr-4">Target Reps</th>
                          <th className="py-2 pr-4">Rest</th>
                          <th className="py-2 pr-4">Target Intensity</th>
                          <th className="py-2">Notes</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/40">
                        {ex.prescribed_sets.map((set) => {
                          const repDisplay =
                            set.target_reps_min && set.target_reps_max
                              ? `${set.target_reps_min}–${set.target_reps_max} reps`
                              : `${set.target_reps} reps`

                          return (
                            <tr key={set.set_number} className="text-slate-300">
                              <td className="py-2 pr-4 font-mono font-bold text-slate-400">
                                Set {set.set_number}
                              </td>
                              <td className="py-2 pr-4 font-semibold text-emerald-300">
                                {repDisplay}
                              </td>
                              <td className="py-2 pr-4 font-mono text-slate-400">
                                {set.rest_seconds}s
                              </td>
                              <td className="py-2 pr-4 font-mono text-amber-300">
                                {set.target_rpe ? `@ RPE ${set.target_rpe}` : 'Moderate'}
                              </td>
                              <td className="py-2 text-[11px] text-slate-400 italic">
                                {set.notes || '—'}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Reasons and Rationale */}
                  <div className="space-y-1.5 pt-2 border-t border-slate-800/60 text-xs">
                    {ex.prescription_rationale && (
                      <p className="text-slate-300 flex items-start gap-1.5">
                        <Activity className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span>
                          <strong className="text-slate-200">Prescription Rationale:</strong>{' '}
                          {ex.prescription_rationale}
                        </span>
                      </p>
                    )}
                    {ex.reasons && ex.reasons.length > 0 && (
                      <p className="text-slate-400 flex items-start gap-1.5">
                        <Info className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5" />
                        <span>
                          <strong className="text-slate-300">Why this exercise:</strong>{' '}
                          {ex.reasons.join(' • ')}
                        </span>
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
