/**
 * Active Program Overview & Week Tracking Presentation Logic (Phase 9C.5.2).
 *
 * Provides authoritative helper functions for:
 * - Tab resolution and URL query synchronization
 * - Program completion percentage arithmetic with zero-division / NaN guards
 * - Split type and phase formatting
 * - Authoritative day state derivation (COMPLETED, CURRENT, UPCOMING, REST)
 * - Week progress tracking
 * - Slot role styling and badge mapping
 * - Guard against static catalog and mock fallback
 */

import type { ProgramResponse, ProgramCompletedWorkout } from '../types/program.ts'
import type { PlannedWorkoutDay, ExerciseSlotRole } from '../types/workoutPlan.ts'

export type ProgramDayState = 'COMPLETED' | 'CURRENT' | 'UPCOMING' | 'REST'

export const SPLIT_LABELS: Record<string, string> = {
  full_body: 'Full Body Split',
  upper_lower: 'Upper / Lower Split',
  push_pull_legs: 'Push / Pull / Legs Split',
}

export const WORKOUT_FILTER_TABS = [
  'All Workouts',
  'Generate Plan',
  'Active Program',
  'Custom Workouts',
  'Favorites',
  'History',
] as const

export type WorkoutFilterTab = (typeof WORKOUT_FILTER_TABS)[number]

/**
 * Maps URL search parameter `tab` to internal active tab name.
 */
export function resolveActiveTabFromParam(
  tabParam: string | null,
  localTab: string = 'All Workouts'
): string {
  if (tabParam === 'program') return 'Active Program'
  if (tabParam === 'generate') return 'Generate Plan'
  return localTab
}

/**
 * Calculates display-only program completion percentage.
 * Guarantees zero-division, NaN, and Infinity protection.
 */
export function calculateProgramCompletionPercentage(
  completedCount: number,
  totalPlanned: number
): { percentage: number; label: string } {
  if (!totalPlanned || totalPlanned <= 0) {
    return { percentage: 0, label: '0 of 0 workouts completed (0%)' }
  }

  const clampedCompleted = Math.max(0, completedCount)
  const rawRatio = clampedCompleted / totalPlanned
  const rawPercentage = Math.round(rawRatio * 100)

  // Guard against NaN or Infinity
  const percentage = Number.isFinite(rawPercentage)
    ? Math.max(0, Math.min(100, rawPercentage))
    : 0

  return {
    percentage,
    label: `${clampedCompleted} of ${totalPlanned} workouts completed (${percentage}%)`,
  }
}

/**
 * Formats split type into human-readable label.
 */
export function formatSplitType(splitType?: string): string {
  if (!splitType) return 'Custom Split'
  return SPLIT_LABELS[splitType] || splitType
}

/**
 * Checks if a specific week and day is completed according to authoritative completedWorkouts list.
 */
export function isDayCompleted(
  completedWorkouts: ProgramCompletedWorkout[] | undefined,
  weekNumber: number,
  dayNumber: number
): boolean {
  if (!completedWorkouts || completedWorkouts.length === 0) return false
  return completedWorkouts.some(
    (cw) =>
      (cw.weekNumber ?? cw.week_number) === weekNumber &&
      (cw.dayNumber ?? cw.day_number) === dayNumber
  )
}

/**
 * Derives authoritative state for a program day:
 * - REST: if day is marked as rest day
 * - COMPLETED: if authoritative session is completed
 * - CURRENT: if matches backend currentWeek/currentDay and program is active
 * - UPCOMING: otherwise
 */
export function deriveProgramDayState(
  day: Partial<PlannedWorkoutDay>,
  weekNumber: number,
  program: Pick<
    ProgramResponse,
    'currentWeek' | 'current_week' | 'currentDay' | 'current_day' | 'status' | 'completedWorkouts' | 'completed_workouts'
  >
): ProgramDayState {
  const isRest = Boolean(day.is_rest_day || day.isRestDay)
  if (isRest) return 'REST'

  const completedList = program.completedWorkouts ?? program.completed_workouts ?? []
  const dayNum = day.day_number ?? day.dayNumber ?? 1
  const completed = isDayCompleted(completedList, weekNumber, dayNum)
  if (completed) return 'COMPLETED'

  const curWeek = program.currentWeek ?? program.current_week ?? 1
  const curDay = program.currentDay ?? program.current_day ?? 1
  const isActive = program.status === 'active'

  if (isActive && weekNumber === curWeek && dayNum === curDay) {
    return 'CURRENT'
  }

  return 'UPCOMING'
}

/**
 * Computes number of completed workouts for a given week.
 */
export function getCompletedDaysCountForWeek(
  completedWorkouts: ProgramCompletedWorkout[] | undefined,
  weekNumber: number
): number {
  if (!completedWorkouts) return 0
  return completedWorkouts.filter(
    (cw) => (cw.weekNumber ?? cw.week_number) === weekNumber
  ).length
}

/**
 * Configuration for slot roles.
 */
export interface SlotRoleMeta {
  label: string
  badgeClass: string
}

export const SLOT_ROLE_CONFIGS: Record<ExerciseSlotRole, SlotRoleMeta> = {
  warmup_corrective: {
    label: 'Warm-up / Prep',
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

export function getSlotRoleMeta(slotRole?: string): SlotRoleMeta {
  if (slotRole && slotRole in SLOT_ROLE_CONFIGS) {
    return SLOT_ROLE_CONFIGS[slotRole as ExerciseSlotRole]
  }
  return {
    label: 'Compound',
    badgeClass: 'bg-slate-800 text-slate-300 border-slate-700',
  }
}
