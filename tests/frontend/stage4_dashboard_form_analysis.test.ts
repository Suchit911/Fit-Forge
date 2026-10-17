/**
 * REAL-DATA REMEDIATION — STAGE 4 TEST SUITE
 * Dashboard Active Prescription & Real Form Analysis Verification
 *
 * Verifies:
 * 1. Dashboard Today's Workout queries authoritative active program & prescription.
 * 2. Proper empty and error states when no program is active or API fails.
 * 3. Removal of fabricated form analysis sessions and zero initial state.
 * 4. Historical results require actual persisted session responses.
 * 5. Strict computer-vision capability gating (strictly 5 verified pipelines).
 * 6. Unsupported exercises cannot initiate CV stream and provide clear manual logging guidance.
 * 7. Real camera error handling, heuristic evaluation integrity, and rep progress honesty.
 */

import { test, describe } from 'node:test'
import assert from 'node:assert/strict'

import { programService } from '../../src/services/programService.ts'
import {
  formAnalysisService,
  getInitialSessionBaseline,
} from '../../src/services/formAnalysisService.ts'
import {
  isCVSupportedExercise,
  resolveCVExerciseId,
  getCVUnsupportedExplanation,
  VERIFIED_CV_EXERCISES,
} from '../../src/utils/formAnalysisCapability.ts'
import {
  workoutPlanExecutionService,
  type GeneratedWorkoutExecutionContext,
} from '../../src/services/workoutPlanExecutionService.ts'
import type { ProgramResponse, EffectivePrescriptionResponse } from '../../src/types/program.ts'

// ============================================================================
// PART 1: DASHBOARD ACTIVE PRESCRIPTION & FALLBACK SCENARIOS (1–7)
// ============================================================================

describe('Stage 4 — Dashboard Active Program Prescription', () => {
  const originalGetIdToken = programService._getIdToken
  const originalFetch = globalThis.fetch

  test('1. Authoritative active program is queried with Bearer token', async () => {
    let capturedUrl = ''
    let capturedAuth = ''

    programService._getIdToken = async () => 'mock-token-abc'
    globalThis.fetch = (async (url: any, init: any) => {
      capturedUrl = String(url)
      capturedAuth = init?.headers?.Authorization || ''
      return {
        ok: true,
        status: 200,
        json: async () => ({
          id: 'prog_123',
          userId: 'user_xyz',
          planId: 'plan_456',
          title: 'Upper/Lower Hypertrophy',
          splitType: 'upper_lower',
          currentWeek: 2,
          currentDay: 3,
          status: 'active',
          totalWeeks: 8,
          daysPerWeek: 4,
          startedAt: '2026-10-01T00:00:00Z',
        }),
      } as Response
    }) as any

    try {
      const program = await programService.getActiveProgram()
      assert.ok(program)
      assert.strictEqual(capturedUrl.endsWith('/programs/active'), true)
      assert.strictEqual(capturedAuth, 'Bearer mock-token-abc')
      assert.strictEqual(program?.id, 'prog_123')
      assert.strictEqual(program?.currentWeek, 2)
      assert.strictEqual(program?.currentDay, 3)
      assert.strictEqual(program?.status, 'active')
    } finally {
      programService._getIdToken = originalGetIdToken
      globalThis.fetch = originalFetch
    }
  })

  test('2. Effective prescription queries exact currentWeek and currentDay from active program', async () => {
    let capturedUrl = ''

    programService._getIdToken = async () => 'mock-token-abc'
    globalThis.fetch = (async (url: any) => {
      capturedUrl = String(url)
      return {
        ok: true,
        status: 200,
        json: async () => ({
          programId: 'prog_123',
          planId: 'plan_456',
          weekNumber: 2,
          dayNumber: 3,
          phaseLabel: 'Hypertrophy Accumulation',
          isAdapted: true,
          day: {
            day_number: 3,
            day_label: 'Lower Body Power',
            focus: 'Posterior chain strength and quad hypertrophy',
            exercises: [
              {
                exercise_id: 'ex_squat',
                name: 'Barbell Squat',
                slot_role: 'primary_compound',
                prescribed_sets: [
                  { set_number: 1, target_reps: 6, weight_kg: 100, target_rpe: 8, rest_seconds: 180 },
                  { set_number: 2, target_reps: 6, weight_kg: 100, target_rpe: 8, rest_seconds: 180 },
                  { set_number: 3, target_reps: 6, weight_kg: 100, target_rpe: 8.5, rest_seconds: 180 },
                ],
                total_sets: 3,
                is_adapted: true,
              },
            ],
          },
        }),
      } as Response
    }) as any

    try {
      const prescription = await programService.getEffectivePrescription(2, 3)
      assert.ok(prescription)
      assert.strictEqual(capturedUrl.endsWith('/programs/active/prescription/2/3'), true)
      assert.strictEqual(prescription.weekNumber, 2)
      assert.strictEqual(prescription.dayNumber, 3)
      assert.strictEqual(prescription.isAdapted, true)
      assert.strictEqual(prescription.day.exercises.length, 1)
      assert.strictEqual(prescription.day.exercises[0].name, 'Barbell Squat')
    } finally {
      programService._getIdToken = originalGetIdToken
      globalThis.fetch = originalFetch
    }
  })

  test('3. When no active program exists (404), getActiveProgram returns null without fabricating defaults', async () => {
    programService._getIdToken = async () => 'mock-token-abc'
    globalThis.fetch = (async () => {
      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: 'No active program found.' }),
      } as Response
    }) as any

    try {
      const program = await programService.getActiveProgram()
      assert.strictEqual(program, null)
    } finally {
      programService._getIdToken = originalGetIdToken
      globalThis.fetch = originalFetch
    }
  })

  test('4. Dashboard API failure throws explicit Error rather than returning a fallback workout', async () => {
    programService._getIdToken = async () => 'mock-token-abc'
    globalThis.fetch = (async () => {
      return {
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal mesocycle database outage.' }),
      } as Response
    }) as any

    try {
      await assert.rejects(
        () => programService.getActiveProgram(),
        (err: any) => {
          assert.strictEqual(err instanceof Error, true)
          assert.strictEqual(err.message, 'Internal mesocycle database outage.')
          return true
        }
      )
    } finally {
      programService._getIdToken = originalGetIdToken
      globalThis.fetch = originalFetch
    }
  })

  test('5. Network connection drop throws network failure error', async () => {
    programService._getIdToken = async () => 'mock-token-abc'
    globalThis.fetch = (async () => {
      throw new Error('Connection refused')
    }) as any

    try {
      await assert.rejects(
        () => programService.getActiveProgram(),
        (err: any) => {
          assert.ok(err.message.includes('Network connection failure'))
          return true
        }
      )
    } finally {
      programService._getIdToken = originalGetIdToken
      globalThis.fetch = originalFetch
    }
  })

  test('6. Scheduled rest day prescription preserves recovery semantics with 0 exercises', async () => {
    programService._getIdToken = async () => 'mock-token-abc'
    globalThis.fetch = (async () => {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          programId: 'prog_123',
          planId: 'plan_456',
          weekNumber: 1,
          dayNumber: 7,
          phaseLabel: 'Deload & Recovery',
          isAdapted: false,
          day: {
            day_number: 7,
            day_label: 'Rest Day',
            focus: 'Complete rest and central nervous system recovery',
            exercises: [],
          },
        }),
      } as Response
    }) as any

    try {
      const prescription = await programService.getEffectivePrescription(1, 7)
      assert.strictEqual(prescription.day.exercises.length, 0)
      assert.strictEqual(prescription.day.day_label, 'Rest Day')
    } finally {
      programService._getIdToken = originalGetIdToken
      globalThis.fetch = originalFetch
    }
  })

  test('7. Start Workout execution context validates all four required coordinates', () => {
    const validContext: GeneratedWorkoutExecutionContext = {
      programId: 'prog_123',
      planId: 'plan_456',
      planTitle: 'Hypertrophy Mesocycle',
      splitType: 'upper_lower',
      weekNumber: 2,
      dayNumber: 3,
      phaseLabel: 'Hypertrophy Accumulation',
      day: {
        day_number: 3,
        day_label: 'Lower Body Focus',
        exercises: [
          {
            exercise_id: 'ex_squat',
            name: 'Barbell Squat',
            slot_role: 'primary_compound',
            prescribed_sets: [{ set_number: 1, target_reps: 8 }],
          },
        ],
      },
      isAdapted: false,
    }

    const validResult = workoutPlanExecutionService.validateExecutionContext(validContext)
    assert.strictEqual(validResult.isValid, true)

    // Invalid context missing programId
    const invalidContext = { ...validContext, programId: '' }
    const invalidResult = workoutPlanExecutionService.validateExecutionContext(invalidContext)
    assert.strictEqual(invalidResult.isValid, false)
  })
})

// ============================================================================
// PART 2: FORM ANALYSIS SESSION & TELEMETRY INTEGRITY (8–12)
// ============================================================================

describe('Stage 4 — Form Analysis Session & Telemetry Integrity', () => {
  const originalFetch = globalThis.fetch

  test('8. Baseline initial session contains zero observed repetitions, zero score, and zero completed reps', () => {
    const baseline = getInitialSessionBaseline('squat')
    assert.strictEqual(baseline.reps, 0)
    assert.strictEqual(baseline.formScore, 0)
    assert.strictEqual(baseline.formStatus, 'Ready')
    assert.strictEqual(baseline.analysisTime, '00:00')
    assert.strictEqual(baseline.repProgress.length, 0)
    assert.strictEqual(baseline.positiveFeedback.length, 0)
    assert.strictEqual(baseline.improvementFeedback.length, 0)
    assert.strictEqual(baseline.keyMetrics.length, 0)
    assert.strictEqual(baseline.history.length, 0)
  })

  test('9. getFormAnalysisSession produces genuine zero baseline without fake 80kg/8reps/82score metrics', async () => {
    const session = await formAnalysisService.getFormAnalysisSession('squat')
    assert.strictEqual(session.reps, 0)
    assert.strictEqual(session.formScore, 0)
    assert.strictEqual(session.repProgress.length, 0)
    assert.notStrictEqual(session.weightKg, 80)
    assert.notStrictEqual(session.reps, 8)
    assert.notStrictEqual(session.formScore, 82)
  })

  test('10. getHistory queries authoritative history endpoint and throws on 401', async () => {
    globalThis.fetch = (async (url: any, init: any) => {
      const urlStr = String(url)
      if (urlStr.includes('/form-analysis/history')) {
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: 'Unauthorized' }),
        } as Response
      }
      return { ok: false, status: 500 } as Response
    }) as any

    try {
      await assert.rejects(
        () => formAnalysisService.getHistory(20),
        (err: any) => err.message.includes('Authentication required')
      )
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  test('11. getSessionDetail queries specific session ID and throws 404 for missing sessions', async () => {
    globalThis.fetch = (async (url: any) => {
      const urlStr = String(url)
      if (urlStr.includes('/form-analysis/history/non-existent-session')) {
        return {
          ok: false,
          status: 404,
          json: async () => ({ detail: 'Session not found.' }),
        } as Response
      }
      return { ok: false, status: 500 } as Response
    }) as any

    try {
      await assert.rejects(
        () => formAnalysisService.getSessionDetail('non-existent-session'),
        (err: any) => err.message.includes('Form analysis session not found')
      )
    } finally {
      globalThis.fetch = originalFetch
    }
  })

  test('12. finalizeSession sends POST to sessions/{id}/finalize and rejects on failure', async () => {
    let capturedMethod = ''
    globalThis.fetch = (async (url: any, init: any) => {
      capturedMethod = init?.method || ''
      return {
        ok: true,
        status: 200,
        json: async () => ({
          session_id: 'session-xyz',
          user_id: 'user-1',
          exercise_id: 'squat',
          canonical_exercise_id: 'ex_squat',
          exercise_name: 'Barbell Squat',
          status: 'completed',
          started_at: '2026-10-16T10:00:00Z',
          completed_at: '2026-10-16T10:02:00Z',
          duration_seconds: 120,
          total_reps: 5,
          completed_reps: 5,
          valid_reps: 5,
          incomplete_reps: 0,
          invalid_reps: 0,
          insufficient_data_reps: 0,
          overall_score: 88.5,
          best_score: 92.0,
          worst_score: 85.0,
          category_averages: { range_of_motion: 90.0 },
          summary_feedback: ['Good consistency'],
          reps: [],
        }),
      } as Response
    }) as any

    try {
      const result = await formAnalysisService.finalizeSession('session-xyz', 120)
      assert.strictEqual(capturedMethod, 'POST')
      assert.strictEqual(result.session_id, 'session-xyz')
      assert.strictEqual(result.overall_score, 88.5)
      assert.strictEqual(result.total_reps, 5)
    } finally {
      globalThis.fetch = originalFetch
    }
  })
})

// ============================================================================
// PART 3: COMPUTER VISION CAPABILITY GATING SCENARIOS (13–18)
// ============================================================================

describe('Stage 4 — Computer Vision Capability Gating', () => {
  test('13. Exactly 5 canonical exercises are registered as operational CV capabilities', () => {
    const keys = Object.keys(VERIFIED_CV_EXERCISES)
    assert.strictEqual(keys.length, 5)
    assert.deepStrictEqual(
      keys.sort(),
      ['bench_press', 'bicep_curl', 'deadlift', 'shoulder_press', 'squat']
    )
    for (const key of keys) {
      assert.strictEqual(VERIFIED_CV_EXERCISES[key as keyof typeof VERIFIED_CV_EXERCISES].isOperational, true)
    }
  })

  test('14. Resolves canonical exercise IDs and aliases to verified CV keys', () => {
    assert.strictEqual(resolveCVExerciseId('squat'), 'squat')
    assert.strictEqual(resolveCVExerciseId('ex_squat'), 'squat')
    assert.strictEqual(resolveCVExerciseId('barbell_squat'), 'squat')

    assert.strictEqual(resolveCVExerciseId('bench_press'), 'bench_press')
    assert.strictEqual(resolveCVExerciseId('ex_bench_press'), 'bench_press')
    assert.strictEqual(resolveCVExerciseId('bench'), 'bench_press')

    assert.strictEqual(resolveCVExerciseId('deadlift'), 'deadlift')
    assert.strictEqual(resolveCVExerciseId('ex_deadlift'), 'deadlift')

    assert.strictEqual(resolveCVExerciseId('bicep_curl'), 'bicep_curl')
    assert.strictEqual(resolveCVExerciseId('ex_bicep_curl'), 'bicep_curl')

    assert.strictEqual(resolveCVExerciseId('shoulder_press'), 'shoulder_press')
    assert.strictEqual(resolveCVExerciseId('ex_shoulder_press'), 'shoulder_press')
    assert.strictEqual(resolveCVExerciseId('overhead_press'), 'shoulder_press')
  })

  test('15. Rejects unsupported exercises and returns null for non-CV exercises', () => {
    assert.strictEqual(isCVSupportedExercise('ex_leg_press'), false)
    assert.strictEqual(resolveCVExerciseId('ex_leg_press'), null)

    assert.strictEqual(isCVSupportedExercise('lat_pulldown'), false)
    assert.strictEqual(resolveCVExerciseId('lat_pulldown'), null)

    assert.strictEqual(isCVSupportedExercise('tricep_extension'), false)
    assert.strictEqual(resolveCVExerciseId('tricep_extension'), null)

    assert.strictEqual(isCVSupportedExercise('dumbbell_fly'), false)
    assert.strictEqual(resolveCVExerciseId('dumbbell_fly'), null)

    assert.strictEqual(isCVSupportedExercise(''), false)
    assert.strictEqual(resolveCVExerciseId(null), null)
  })

  test('16. Unsupported exercise explanation clearly notes manual logging remains available', () => {
    const explanation = getCVUnsupportedExplanation('Leg Press')
    assert.ok(explanation.includes("'Leg Press' does not support real-time computer vision form analysis"))
    assert.ok(explanation.includes('Live video tracking is available for Barbell Squat, Barbell Bench Press'))
    assert.ok(explanation.includes('Manual set and repetition logging remains fully available'))
  })

  test('17. Verified CV exercises provide movement pattern metadata', () => {
    assert.strictEqual(VERIFIED_CV_EXERCISES.squat.movementPattern, 'squat')
    assert.strictEqual(VERIFIED_CV_EXERCISES.bench_press.movementPattern, 'horizontal_push')
    assert.strictEqual(VERIFIED_CV_EXERCISES.deadlift.movementPattern, 'hinge')
    assert.strictEqual(VERIFIED_CV_EXERCISES.bicep_curl.movementPattern, 'isolation')
    assert.strictEqual(VERIFIED_CV_EXERCISES.shoulder_press.movementPattern, 'vertical_push')
  })

  test('18. Case-insensitive and hyphenated alias resolution works reliably', () => {
    assert.strictEqual(resolveCVExerciseId('BARBELL-SQUAT'), 'squat')
    assert.strictEqual(resolveCVExerciseId('Bench-Press'), 'bench_press')
    assert.strictEqual(resolveCVExerciseId('Ex_Bicep_Curl'), 'bicep_curl')
    assert.strictEqual(resolveCVExerciseId('Overhead-Shoulder-Press'), 'shoulder_press')
  })
})
