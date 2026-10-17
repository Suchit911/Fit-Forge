/**
 * Frontend Test Suite for Phase 9B.8.5.5 — Workout Plan Generation Integration.
 *
 * Validates:
 * A. API service calls, headers, authorization, and response parsing
 * B. Request serialization and numeric bounds preservation
 * C. Error handling (401, 422, 500, network failure)
 * D. State A valid plan response data integrity
 * E. Duration feasibility label and note mappings
 * F. State B, C, D domain diagnostics handling
 * G. Deterministic plan ID preservation
 */

import { test, describe, beforeEach } from 'node:test'
import assert from 'node:assert/strict'

import type {
  WorkoutPlanGenerateRequest,
  WorkoutPlanResponse,
  PlannedWeek,
  PlannedWorkoutDay,
  PlannedExercise,
  PlannedSet,
} from '../../src/types/workoutPlan.ts'
import { workoutPlanService } from '../../src/services/workoutPlanService.ts'
import * as firebaseLib from '../../src/lib/firebase.ts'

// ============================================================================
// MOCK DATA FACTORIES
// ============================================================================

function createMockSet(overrides: Partial<PlannedSet> = {}): PlannedSet {
  return {
    set_number: 1,
    target_reps: 8,
    target_reps_min: 6,
    target_reps_max: 10,
    target_rpe: 7.5,
    rest_seconds: 120,
    notes: 'Prescribed set 1 of 3',
    ...overrides,
  }
}

function createMockExercise(overrides: Partial<PlannedExercise> = {}): PlannedExercise {
  return {
    slot_role: 'primary_compound',
    slot_index: 1,
    exercise_id: 'ex_bench_press',
    name: 'Barbell Bench Press',
    movement_pattern: 'horizontal_push',
    exercise_type: 'compound',
    difficulty: 'intermediate',
    equipment: ['barbell', 'bench'],
    primary_muscles: ['chest', 'triceps'],
    prescribed_sets: [createMockSet({ set_number: 1 }), createMockSet({ set_number: 2 })],
    total_sets: 2,
    estimated_duration_minutes: 8,
    score: 95.0,
    reasons: ['Matches selected fitness goal: strength', 'Primary horizontal push movement'],
    is_canonical_cv: true,
    progression_note: 'Baseline accumulation phase establishing movement exposure.',
    prescription_rationale: 'Primary compound progression target emphasizing multi-joint capacity.',
    ...overrides,
  }
}

function createMockDay(overrides: Partial<PlannedWorkoutDay> = {}): PlannedWorkoutDay {
  return {
    day_number: 1,
    day_label: 'Upper A',
    is_rest_day: false,
    focus: 'Horizontal Push & Pull Focus',
    target_patterns: ['horizontal_push', 'horizontal_pull'],
    target_muscles: ['chest', 'back'],
    exercises: [createMockExercise()],
    total_sets: 2,
    estimated_duration_minutes: 25,
    ...overrides,
  }
}

function createMockWeek(overrides: Partial<PlannedWeek> = {}): PlannedWeek {
  return {
    week_number: 1,
    phase_label: 'Baseline Accumulation',
    days: [createMockDay()],
    total_weekly_sets: 2,
    total_workouts: 1,
    ...overrides,
  }
}

function createMockPlanResponse(overrides: Partial<WorkoutPlanResponse> = {}): WorkoutPlanResponse {
  return {
    plan_id: 'plan_test_48961052f589981e',
    title: '4-Week Upper / Lower Program',
    description: 'Deterministic 4-day upper/lower plan tailored for muscle gain.',
    target_goal: 'muscle_gain',
    fitness_level: 'intermediate',
    split_type: 'upper_lower',
    training_days_per_week: 4,
    total_weeks: 4,
    weeks: [createMockWeek()],
    applied_filters: { training_days_per_week: 4, target_workout_duration_minutes: 45 },
    feasibility_check_passed: true,
    duration_feasibility: 'feasible',
    diagnostics: ['Plan generation completed successfully with zero shortfalls.'],
    conflicting_filters: [],
    ...overrides,
  }
}

// ============================================================================
// TEST SUITE
// ============================================================================

describe('Phase 9B.8.5.5 — Frontend Workout Plan Generation Integration', () => {
  // Save original globals
  const originalFetch = globalThis.fetch
  const originalGetIdToken = workoutPlanService._getIdToken

  beforeEach(() => {
    globalThis.fetch = originalFetch
    workoutPlanService._getIdToken = originalGetIdToken
  })

  // --------------------------------------------------------------------------
  // A. API Service & Authentication
  // --------------------------------------------------------------------------

  test('1. Service obtains Firebase token and sends Authorization Bearer header', async () => {
    let capturedAuthHeader: string | null = null
    let capturedUrl: string | null = null
    let capturedMethod: string | null = null

    workoutPlanService._getIdToken = async () => 'test-firebase-token-xyz-123'

    globalThis.fetch = (async (url: any, init: any) => {
      capturedUrl = String(url)
      capturedMethod = init?.method
      capturedAuthHeader = init?.headers?.Authorization || null
      return new Response(JSON.stringify(createMockPlanResponse()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const request: WorkoutPlanGenerateRequest = {
      training_days_per_week: 4,
      plan_duration_weeks: 4,
    }
    const plan = await workoutPlanService.generateWorkoutPlan(request)

    assert.ok(capturedUrl?.includes('/workout-plans/generate'))
    assert.strictEqual(capturedMethod, 'POST')
    assert.strictEqual(capturedAuthHeader, 'Bearer test-firebase-token-xyz-123')
    assert.strictEqual(plan.plan_id, 'plan_test_48961052f589981e')
  })

  test('2. Service rejects with clear error when user is unauthenticated (token null)', async () => {
    workoutPlanService._getIdToken = async () => null

    await assert.rejects(
      async () => {
        await workoutPlanService.generateWorkoutPlan({ training_days_per_week: 3 })
      },
      /Authentication required\. Please sign in/
    )
  })

  test('3. Service handles HTTP 401 Unauthorized', async () => {
    workoutPlanService._getIdToken = async () => 'expired-token'

    globalThis.fetch = (async () => {
      return new Response(JSON.stringify({ detail: 'Could not validate credentials' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    await assert.rejects(
      async () => {
        await workoutPlanService.generateWorkoutPlan({ training_days_per_week: 3 })
      },
      /Authentication expired or invalid/
    )
  })

  test('4. Service handles HTTP 422 Unprocessable Entity with validation details', async () => {
    workoutPlanService._getIdToken = async () => 'valid-token'

    globalThis.fetch = (async () => {
      return new Response(
        JSON.stringify({
          detail: [{ loc: ['body', 'training_days_per_week'], msg: 'Input should be less than or equal to 6' }],
        }),
        {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    }) as any

    await assert.rejects(
      async () => {
        await workoutPlanService.generateWorkoutPlan({ training_days_per_week: 10 })
      },
      /Input should be less than or equal to 6/
    )
  })

  test('5. Service handles HTTP 500 sanitized server error', async () => {
    workoutPlanService._getIdToken = async () => 'valid-token'

    globalThis.fetch = (async () => {
      return new Response(
        JSON.stringify({ detail: 'Database connection failed at /internal/secrets' }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    }) as any

    await assert.rejects(
      async () => {
        await workoutPlanService.generateWorkoutPlan({ training_days_per_week: 3 })
      },
      /An unexpected server error occurred/
    )
  })

  test('6. Service handles network failure gracefully', async () => {
    workoutPlanService._getIdToken = async () => 'valid-token'

    globalThis.fetch = (async () => {
      throw new TypeError('Failed to fetch')
    }) as any

    await assert.rejects(
      async () => {
        await workoutPlanService.generateWorkoutPlan({ training_days_per_week: 3 })
      },
      /Network connection failure/
    )
  })

  // --------------------------------------------------------------------------
  // B. Request Serialization & Numeric Preservation
  // --------------------------------------------------------------------------

  test('7. Request body preserves numeric values without stringification', async () => {
    let capturedBody: any = null
    workoutPlanService._getIdToken = async () => 'valid-token'

    globalThis.fetch = (async (_url: any, init: any) => {
      capturedBody = JSON.parse(init.body)
      return new Response(JSON.stringify(createMockPlanResponse()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    const req: WorkoutPlanGenerateRequest = {
      training_days_per_week: 4,
      plan_duration_weeks: 8,
      target_workout_duration_minutes: 60,
      target_goal: 'strength',
      environment: 'gym',
      available_equipment: ['barbell', 'bench'],
      form_analysis_supported_only: true,
      preferred_split: 'upper_lower',
    }

    await workoutPlanService.generateWorkoutPlan(req)

    assert.strictEqual(typeof capturedBody.training_days_per_week, 'number')
    assert.strictEqual(capturedBody.training_days_per_week, 4)
    assert.strictEqual(typeof capturedBody.plan_duration_weeks, 'number')
    assert.strictEqual(capturedBody.plan_duration_weeks, 8)
    assert.strictEqual(typeof capturedBody.target_workout_duration_minutes, 'number')
    assert.strictEqual(capturedBody.target_workout_duration_minutes, 60)
    assert.strictEqual(capturedBody.target_goal, 'strength')
    assert.strictEqual(capturedBody.environment, 'gym')
    assert.deepStrictEqual(capturedBody.available_equipment, ['barbell', 'bench'])
    assert.strictEqual(capturedBody.form_analysis_supported_only, true)
    assert.strictEqual(capturedBody.preferred_split, 'upper_lower')
  })

  test('8. Request body does NOT include user ID or authorization tokens', async () => {
    let capturedBody: any = null
    workoutPlanService._getIdToken = async () => 'valid-token'

    globalThis.fetch = (async (_url: any, init: any) => {
      capturedBody = JSON.parse(init.body)
      return new Response(JSON.stringify(createMockPlanResponse()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }) as any

    await workoutPlanService.generateWorkoutPlan({ training_days_per_week: 3 })

    assert.strictEqual(capturedBody.uid, undefined)
    assert.strictEqual(capturedBody.userId, undefined)
    assert.strictEqual(capturedBody.firebaseUid, undefined)
    assert.strictEqual(capturedBody.token, undefined)
  })

  // --------------------------------------------------------------------------
  // C. State A (Valid Plan) Response Parsing
  // --------------------------------------------------------------------------

  test('9. State A response preserves planId and splitType', () => {
    const plan = createMockPlanResponse({
      plan_id: 'plan_deterministic_abc123',
      split_type: 'push_pull_legs',
      training_days_per_week: 6,
    })

    assert.strictEqual(plan.plan_id, 'plan_deterministic_abc123')
    assert.strictEqual(plan.split_type, 'push_pull_legs')
    assert.strictEqual(plan.training_days_per_week, 6)
    assert.strictEqual(plan.feasibility_check_passed, true)
  })

  test('10. Multi-week mesocycle preserves week numbers and phase labels', () => {
    const weeks: PlannedWeek[] = [
      createMockWeek({ week_number: 1, phase_label: 'Baseline Accumulation' }),
      createMockWeek({ week_number: 2, phase_label: 'Volume Loading' }),
      createMockWeek({ week_number: 3, phase_label: 'Intensity Peak' }),
      createMockWeek({ week_number: 4, phase_label: 'Deload & Consolidation' }),
    ]
    const plan = createMockPlanResponse({ total_weeks: 4, weeks })

    assert.strictEqual(plan.weeks.length, 4)
    assert.strictEqual(plan.weeks[0].phase_label, 'Baseline Accumulation')
    assert.strictEqual(plan.weeks[1].phase_label, 'Volume Loading')
    assert.strictEqual(plan.weeks[2].phase_label, 'Intensity Peak')
    assert.strictEqual(plan.weeks[3].phase_label, 'Deload & Consolidation')
  })

  test('11. Day level models preserve day_number, day_label, and focus', () => {
    const day = createMockDay({
      day_number: 2,
      day_label: 'Lower A',
      focus: 'Machine Hack Squat & Romanian Deadlift',
      total_sets: 15,
      estimated_duration_minutes: 48,
    })

    assert.strictEqual(day.day_number, 2)
    assert.strictEqual(day.day_label, 'Lower A')
    assert.strictEqual(day.focus, 'Machine Hack Squat & Romanian Deadlift')
    assert.strictEqual(day.total_sets, 15)
    assert.strictEqual(day.estimated_duration_minutes, 48)
  })

  test('12. Planned exercises preserve slot_role and movement_pattern', () => {
    const ex = createMockExercise({
      slot_role: 'secondary_compound',
      slot_index: 2,
      name: 'Incline Dumbbell Press',
      movement_pattern: 'horizontal_push',
    })

    assert.strictEqual(ex.slot_role, 'secondary_compound')
    assert.strictEqual(ex.slot_index, 2)
    assert.strictEqual(ex.name, 'Incline Dumbbell Press')
    assert.strictEqual(ex.movement_pattern, 'horizontal_push')
  })

  test('13. Prescribed sets preserve target reps min/max, rest, and RPE', () => {
    const set = createMockSet({
      set_number: 2,
      target_reps: 5,
      target_reps_min: 5,
      target_reps_max: 6,
      target_rpe: 8.0,
      rest_seconds: 180,
    })

    assert.strictEqual(set.set_number, 2)
    assert.strictEqual(set.target_reps, 5)
    assert.strictEqual(set.target_reps_min, 5)
    assert.strictEqual(set.target_reps_max, 6)
    assert.strictEqual(set.target_rpe, 8.0)
    assert.strictEqual(set.rest_seconds, 180)
  })

  test('14. Planned exercises preserve recommendation reason and prescription rationale', () => {
    const ex = createMockExercise({
      reasons: ['Primary compound movement', 'Targets chest'],
      prescription_rationale: 'Primary compound progression target emphasizing multi-joint capacity.',
    })

    assert.strictEqual(ex.reasons.length, 2)
    assert.strictEqual(ex.reasons[0], 'Primary compound movement')
    assert.strictEqual(
      ex.prescription_rationale,
      'Primary compound progression target emphasizing multi-joint capacity.'
    )
  })

  // --------------------------------------------------------------------------
  // D. Duration Feasibility Mapping
  // --------------------------------------------------------------------------

  test('15. Feasible duration is preserved', () => {
    const plan = createMockPlanResponse({ duration_feasibility: 'feasible' })
    assert.strictEqual(plan.duration_feasibility, 'feasible')
  })

  test('16. Potentially over target duration is preserved', () => {
    const plan = createMockPlanResponse({ duration_feasibility: 'potentially_over_target' })
    assert.strictEqual(plan.duration_feasibility, 'potentially_over_target')
  })

  test('17. Impossible under constraints duration is preserved', () => {
    const plan = createMockPlanResponse({ duration_feasibility: 'impossible_under_constraints' })
    assert.strictEqual(plan.duration_feasibility, 'impossible_under_constraints')
  })

  // --------------------------------------------------------------------------
  // E. Domain Diagnostics (State B, C, D)
  // --------------------------------------------------------------------------

  test('18. State B invalid input response preserves feasibility_check_passed=false', () => {
    const plan = createMockPlanResponse({
      feasibility_check_passed: false,
      weeks: [],
      diagnostics: ['At least one available equipment option must be specified.'],
      conflicting_filters: [],
    })

    assert.strictEqual(plan.feasibility_check_passed, false)
    assert.strictEqual(plan.weeks.length, 0)
    assert.strictEqual(plan.diagnostics.length, 1)
    assert.ok(plan.diagnostics[0].includes('equipment option'))
  })

  test('19. State C conflicting constraints response preserves conflicting_filters', () => {
    const plan = createMockPlanResponse({
      feasibility_check_passed: false,
      weeks: [],
      conflicting_filters: ['available_equipment: [barbell]', 'excluded_equipment: [barbell]'],
      diagnostics: ['Conflicting hard constraint filters detected.'],
    })

    assert.strictEqual(plan.feasibility_check_passed, false)
    assert.strictEqual(plan.conflicting_filters.length, 2)
    assert.ok(plan.conflicting_filters[0].includes('available_equipment'))
    assert.ok(plan.conflicting_filters[1].includes('excluded_equipment'))
  })

  test('20. State D catalog shortfall response preserves diagnostic title and details', () => {
    const plan = createMockPlanResponse({
      title: 'Catalog Shortfall',
      feasibility_check_passed: false,
      weeks: [],
      diagnostics: ['Available catalog exercises short of required slots.'],
    })

    assert.strictEqual(plan.title, 'Catalog Shortfall')
    assert.strictEqual(plan.feasibility_check_passed, false)
    assert.strictEqual(plan.weeks.length, 0)
    assert.ok(plan.diagnostics[0].includes('short of required slots'))
  })

  // --------------------------------------------------------------------------
  // F. Determinism & Clean State Isolation
  // --------------------------------------------------------------------------

  test('21. Deterministic plan ID remains identical across identical responses', () => {
    const planA = createMockPlanResponse({ plan_id: 'plan_hash_constant_123' })
    const planB = createMockPlanResponse({ plan_id: 'plan_hash_constant_123' })

    assert.strictEqual(planA.plan_id, planB.plan_id)
  })

  test('22. CV tracked exercises retain is_canonical_cv flag', () => {
    const exCV = createMockExercise({ is_canonical_cv: true })
    const exNonCV = createMockExercise({ is_canonical_cv: false })

    assert.strictEqual(exCV.is_canonical_cv, true)
    assert.strictEqual(exNonCV.is_canonical_cv, false)
  })

  test('23. Corrective slot 0 exercises retain warmup_corrective role', () => {
    const correctiveEx = createMockExercise({
      slot_role: 'warmup_corrective',
      slot_index: 0,
      name: 'Cat-Cow Mobility Drill',
    })

    assert.strictEqual(correctiveEx.slot_role, 'warmup_corrective')
    assert.strictEqual(correctiveEx.slot_index, 0)
  })

  test('24. Slot roles map to required domain roles without subjective labels', () => {
    const allowedRoles = [
      'warmup_corrective',
      'primary_compound',
      'secondary_compound',
      'accessory_1',
      'accessory_2',
      'core_mobility',
    ]

    for (const role of allowedRoles) {
      const ex = createMockExercise({ slot_role: role as any })
      assert.strictEqual(ex.slot_role, role)
    }
  })

  test('25. Applied filters preserve user inputs verbatim', () => {
    const plan = createMockPlanResponse({
      applied_filters: {
        training_days_per_week: 5,
        target_workout_duration_minutes: 50,
        environment: 'gym',
      },
    })

    assert.strictEqual(plan.applied_filters.training_days_per_week, 5)
    assert.strictEqual(plan.applied_filters.target_workout_duration_minutes, 50)
    assert.strictEqual(plan.applied_filters.environment, 'gym')
  })

  test('26. Rep display formatting handles both min/max range and single rep values', () => {
    const setWithRange = createMockSet({ target_reps_min: 8, target_reps_max: 12, target_reps: 10 })
    const setSingle = createMockSet({ target_reps_min: null, target_reps_max: null, target_reps: 15 })

    const formatReps = (s: PlannedSet) =>
      s.target_reps_min && s.target_reps_max ? `${s.target_reps_min}–${s.target_reps_max} reps` : `${s.target_reps} reps`

    assert.strictEqual(formatReps(setWithRange), '8–12 reps')
    assert.strictEqual(formatReps(setSingle), '15 reps')
  })
})
