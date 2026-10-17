/**
 * Workout Plan Execution Service (Phase 9B.8.6).
 *
 * Coordinates in-memory execution context for performing a generated workout day
 * via the active workout experience.
 *
 * Architectural constraints:
 * - 100% ephemeral in-memory state: NO localStorage, NO sessionStorage, NO IndexedDB.
 * - Zero persistence of multi-week plans to Firestore in this phase.
 * - Authoritative backend workout sessions remain the single source of truth.
 */

import type {
  PlannedWorkoutDay,
  WorkoutSplitType,
} from '../types/workoutPlan'

export interface BaseGeneratedWorkoutExecutionContext {
  planId: string
  planTitle: string
  splitType: WorkoutSplitType
  weekNumber: number
  phaseLabel: string
  day: PlannedWorkoutDay
  baseWorkoutId?: string
  isAdapted?: boolean
}

/**
 * Program Execution Context: Requires all four program coordinates:
 * programId, planId, weekNumber, and dayNumber.
 */
export interface ProgramWorkoutExecutionContext extends BaseGeneratedWorkoutExecutionContext {
  programId: string
  dayNumber: number
}

/**
 * Standalone Generated Workout Context: Does not have programId; dayNumber is optional.
 */
export interface StandaloneGeneratedExecutionContext extends BaseGeneratedWorkoutExecutionContext {
  programId?: undefined
  dayNumber?: number
}

export type GeneratedWorkoutExecutionContext =
  | ProgramWorkoutExecutionContext
  | StandaloneGeneratedExecutionContext

let _activeExecutionContext: GeneratedWorkoutExecutionContext | null = null

/**
 * Resolves an appropriate base static workout ID for backend API route compatibility
 * with POST /api/v1/workouts/{workout_id}/sessions.
 *
 * NOTE: As verified in Phase 9B.8.6 architecture audit, the backend session schema
 * stores `workoutId` as a metadata reference and `completedSets` by canonical `exerciseId`.
 * The Active Workout page in generated mode renders the exact PlannedWorkoutDay exercises,
 * never substituting static workout exercises.
 */
export function resolveBaseWorkoutId(
  day: PlannedWorkoutDay,
  splitType?: WorkoutSplitType
): string {
  const focus = (day.focus || '').toLowerCase()
  const label = (day.day_label || '').toLowerCase()
  const muscles = (day.target_muscles || []).map((m) => m.toLowerCase())
  const patterns = (day.target_patterns || []).map((p) => p.toLowerCase())

  // 1. Core & Abs check
  if (
    focus.includes('core') ||
    focus.includes('abs') ||
    label.includes('core') ||
    muscles.includes('core') ||
    muscles.includes('abs')
  ) {
    return 'wkt_core_abs'
  }

  // 2. Mobility / Recovery check
  if (
    focus.includes('mobility') ||
    focus.includes('recovery') ||
    focus.includes('flexibility') ||
    label.includes('mobility')
  ) {
    return 'wkt_mobility'
  }

  // 3. Full body check
  if (
    splitType === 'full_body' ||
    focus.includes('full body') ||
    label.includes('full body')
  ) {
    return 'wkt_full_hiit'
  }

  // 4. Lower body / legs check
  if (
    focus.includes('lower') ||
    focus.includes('leg') ||
    focus.includes('quad') ||
    label.includes('lower') ||
    muscles.includes('quadriceps') ||
    muscles.includes('hamstrings') ||
    muscles.includes('glutes') ||
    patterns.includes('squat') ||
    patterns.includes('hinge') ||
    patterns.includes('lunge')
  ) {
    return 'wkt_lower_strength'
  }

  // 5. Upper Push check (prioritizes push keywords)
  if (
    focus.includes('push') ||
    label.includes('push') ||
    (muscles.includes('chest') && !muscles.includes('back'))
  ) {
    return 'wkt_upper_push'
  }

  // 6. Upper Pull check
  if (
    focus.includes('pull') ||
    label.includes('pull') ||
    muscles.includes('back') ||
    muscles.includes('biceps')
  ) {
    return 'wkt_upper_pull'
  }

  // 7. Pattern fallback
  if (patterns.includes('horizontal_push') || patterns.includes('vertical_push')) {
    return 'wkt_upper_push'
  }
  if (patterns.includes('vertical_pull') || patterns.includes('horizontal_pull')) {
    return 'wkt_upper_pull'
  }

  // Default canonical reference
  return 'wkt_upper_push'
}

/**
 * Validates a generated workout execution context.
 * Enforces the invariant:
 * If programId is present, all four coordinates (programId, planId, weekNumber, dayNumber) are strictly required.
 * For standalone generated execution without programId, dayNumber remains optional.
 */
export function validateExecutionContext(
  context: unknown
): { isValid: boolean; isProgramMode?: boolean; error?: string } {
  if (!context || typeof context !== 'object') {
    return { isValid: false, isProgramMode: false, error: 'Execution context is null or not an object.' }
  }
  const c = context as Partial<BaseGeneratedWorkoutExecutionContext & { programId?: string; dayNumber?: number }>
  if (!c.planId || typeof c.planId !== 'string' || c.planId.trim() === '') {
    return { isValid: false, isProgramMode: false, error: 'Missing or invalid planId.' }
  }
  if (!c.day || !Array.isArray(c.day.exercises) || c.day.exercises.length === 0) {
    return { isValid: false, isProgramMode: false, error: 'Context missing valid PlannedWorkoutDay exercises.' }
  }
  if (typeof c.weekNumber !== 'number' || !Number.isInteger(c.weekNumber) || c.weekNumber < 1) {
    return { isValid: false, isProgramMode: false, error: 'Invalid or non-positive weekNumber.' }
  }
  // Program Execution Invariant:
  // If programId is defined, all four coordinates (programId, planId, weekNumber, dayNumber) are strictly required.
  const isProgram = c.programId !== undefined && c.programId !== null
  if (isProgram) {
    if (typeof c.programId !== 'string' || c.programId.trim() === '') {
      return { isValid: false, isProgramMode: true, error: 'Invalid programId.' }
    }
    if (typeof c.dayNumber !== 'number' || !Number.isInteger(c.dayNumber) || c.dayNumber < 1) {
      return { isValid: false, isProgramMode: true, error: 'Program execution requires a valid positive integer dayNumber.' }
    }
  }
  return { isValid: true, isProgramMode: isProgram }
}

/**
 * Calculates elapsed workout duration in seconds between session start and completion.
 * Guards against negative, NaN, or non-finite values.
 */
export function calculateElapsedDurationSeconds(
  startTimestamp: number | string | Date,
  endTimestamp: number | string | Date = Date.now()
): number {
  const startEpoch = typeof startTimestamp === 'number'
    ? startTimestamp
    : new Date(startTimestamp).getTime()
  const endEpoch = typeof endTimestamp === 'number'
    ? endTimestamp
    : new Date(endTimestamp).getTime()

  if (isNaN(startEpoch) || isNaN(endEpoch)) {
    return 0
  }

  const elapsedMs = endEpoch - startEpoch
  if (elapsedMs <= 0) {
    return 0
  }

  const seconds = Math.floor(elapsedMs / 1000)
  return Number.isFinite(seconds) && seconds >= 0 ? seconds : 0
}

export const workoutPlanExecutionService = {
  /**
   * Sets the active in-memory generated workout execution context.
   */
  setActiveExecutionContext(context: GeneratedWorkoutExecutionContext): void {
    const validation = validateExecutionContext(context)
    if (!validation.isValid) {
      throw new Error(`Invalid execution context: ${validation.error}`)
    }
    _activeExecutionContext = {
      ...context,
      day: {
        ...context.day,
        exercises: context.day.exercises.map((ex) => {
          const sets = ex.prescribed_sets || (ex as any).prescribedSets || []
          return {
            ...ex,
            prescribed_sets: sets.map((s: any) => ({ ...s })),
            equipment: [...(ex.equipment || [])],
            primary_muscles: [...(ex.primary_muscles || (ex as any).primaryMuscles || [])],
            reasons: [...(ex.reasons || [])],
          }
        }),
        target_patterns: [...(context.day.target_patterns || (context.day as any).targetPatterns || [])],
        target_muscles: [...(context.day.target_muscles || (context.day as any).targetMuscles || [])],
      },
    } as GeneratedWorkoutExecutionContext
  },

  /**
   * Retrieves the current in-memory execution context, or null if none active.
   */
  getActiveExecutionContext(): GeneratedWorkoutExecutionContext | null {
    return _activeExecutionContext
  },

  /**
   * Clears the in-memory execution context upon session completion or cancellation.
   */
  clearActiveExecutionContext(): void {
    _activeExecutionContext = null
  },

  /**
   * Checks whether an in-memory execution context currently exists.
   */
  hasActiveExecutionContext(): boolean {
    return _activeExecutionContext !== null
  },

  /**
   * Helper to resolve the base workout ID.
   */
  resolveBaseWorkoutId,

  /**
   * Validates execution context and enforces program execution invariants.
   */
  validateExecutionContext,

  /**
   * Computes elapsed workout duration in seconds.
   */
  calculateElapsedDurationSeconds,
}
