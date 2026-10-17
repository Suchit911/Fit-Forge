/**
 * Authoritative Computer Vision (CV) Capability & Pipeline Contract (Phase 9B / Stage 4).
 *
 * Derives strictly from the backend CV pipeline registration:
 * Exactly 5 canonical exercises are supported by the computer vision pose tracking engine:
 * 1. Barbell Squat (ex_squat / squat)
 * 2. Barbell Bench Press (ex_bench_press / bench_press)
 * 3. Conventional Deadlift (ex_deadlift / deadlift)
 * 4. Bicep Curl (ex_bicep_curl / bicep_curl)
 * 5. Overhead Shoulder Press (ex_shoulder_press / shoulder_press)
 *
 * Non-supported exercises MUST NOT initiate a CV stream, and must display an explicit
 * explanation that manual set and rep logging remains fully operational.
 */

import type { SupportedExerciseId } from '../types/formStream'

export interface CVExerciseCapability {
  id: SupportedExerciseId
  canonicalId: string
  name: string
  targetMuscles: string
  movementPattern: string
  isOperational: boolean
}

export const VERIFIED_CV_EXERCISES: Record<SupportedExerciseId, CVExerciseCapability> = {
  squat: {
    id: 'squat',
    canonicalId: 'ex_squat',
    name: 'Barbell Squat',
    targetMuscles: 'Quadriceps, Glutes, Hamstrings',
    movementPattern: 'squat',
    isOperational: true,
  },
  bench_press: {
    id: 'bench_press',
    canonicalId: 'ex_bench_press',
    name: 'Barbell Bench Press',
    targetMuscles: 'Pectorals, Triceps, Anterior Deltoids',
    movementPattern: 'horizontal_push',
    isOperational: true,
  },
  deadlift: {
    id: 'deadlift',
    canonicalId: 'ex_deadlift',
    name: 'Conventional Deadlift',
    targetMuscles: 'Posterior Chain, Glutes, Erector Spinae',
    movementPattern: 'hinge',
    isOperational: true,
  },
  bicep_curl: {
    id: 'bicep_curl',
    canonicalId: 'ex_bicep_curl',
    name: 'Bicep Curl',
    targetMuscles: 'Biceps Brachii, Brachialis',
    movementPattern: 'isolation',
    isOperational: true,
  },
  shoulder_press: {
    id: 'shoulder_press',
    canonicalId: 'ex_shoulder_press',
    name: 'Overhead Shoulder Press',
    targetMuscles: 'Deltoids, Upper Pectorals, Triceps',
    movementPattern: 'vertical_push',
    isOperational: true,
  },
}

/**
 * Mapping of canonical catalog IDs and common aliases to the 5 supported CV exercise keys.
 */
const CV_ALIAS_MAP: Record<string, SupportedExerciseId> = {
  // Squat
  squat: 'squat',
  ex_squat: 'squat',
  barbell_squat: 'squat',
  ex_barbell_squat: 'squat',

  // Bench Press
  bench_press: 'bench_press',
  ex_bench_press: 'bench_press',
  bench: 'bench_press',
  barbell_bench_press: 'bench_press',
  ex_barbell_bench_press: 'bench_press',

  // Deadlift
  deadlift: 'deadlift',
  ex_deadlift: 'deadlift',
  conventional_deadlift: 'deadlift',
  ex_conventional_deadlift: 'deadlift',

  // Bicep Curl
  bicep_curl: 'bicep_curl',
  ex_bicep_curl: 'bicep_curl',
  dumbbell_bicep_curl: 'bicep_curl',
  ex_dumbbell_bicep_curl: 'bicep_curl',

  // Shoulder Press
  shoulder_press: 'shoulder_press',
  ex_shoulder_press: 'shoulder_press',
  overhead_press: 'shoulder_press',
  ex_overhead_press: 'shoulder_press',
  overhead_shoulder_press: 'shoulder_press',
  ex_overhead_shoulder_press: 'shoulder_press',
}

/**
 * Resolves an exercise ID or alias to one of the 5 verified CV exercise IDs.
 * Returns null if the exercise does not have a verified CV pipeline.
 */
export function resolveCVExerciseId(exerciseIdOrName?: string | null): SupportedExerciseId | null {
  if (!exerciseIdOrName || typeof exerciseIdOrName !== 'string') return null
  const normalized = exerciseIdOrName.trim().toLowerCase().replace(/-/g, '_')
  return CV_ALIAS_MAP[normalized] || null
}

/**
 * Checks whether an exercise is supported by the computer-vision tracking engine.
 */
export function isCVSupportedExercise(exerciseIdOrName?: string | null): boolean {
  return resolveCVExerciseId(exerciseIdOrName) !== null
}

/**
 * Returns an authoritative explanation when an exercise is not supported by computer vision.
 */
export function getCVUnsupportedExplanation(exerciseName?: string): string {
  const prefix = exerciseName ? `'${exerciseName}' does not support` : 'This exercise does not support'
  return `${prefix} real-time computer vision form analysis. Live video tracking is available for Barbell Squat, Barbell Bench Press, Conventional Deadlift, Bicep Curl, and Overhead Shoulder Press. Manual set and repetition logging remains fully available.`
}
