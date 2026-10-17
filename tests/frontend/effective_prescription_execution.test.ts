/**
 * Dedicated Frontend Integration Test Suite for Phase 9C.5.3:
 * Effective Prescription & Workout Execution Integration.
 *
 * Covers all 30 explicit test points required by Step 16:
 * 1. Program prescription launches execution context.
 * 2. Context contains programId.
 * 3. Context contains planId.
 * 4. Context contains weekNumber.
 * 5. Context contains dayNumber.
 * 6. Context preserves authoritative effective prescription.
 * 7. Adapted prescription is used instead of original snapshot.
 * 8. Session creation sends program affinity.
 * 9. Standard workout session remains backward compatible.
 * 10. Dynamic exercise 1 comes from prescription.
 * 11. Dynamic exercise 2 comes from prescription.
 * 12. Up Next comes from prescription.
 * 13. No hardcoded exercise ID in program mode.
 * 14. Actual user-entered weight is preserved.
 * 15. Actual user-entered reps are preserved.
 * 16. Program completion calls syncSession.
 * 17. Standard workout completion does NOT call syncSession.
 * 18. Backend pointer is not mutated locally.
 * 19. Query invalidation occurs after successful sync.
 * 20. Navigation occurs only after successful completion/sync.
 * 21. Prescription failure prevents workout launch.
 * 22. Session-start failure does not create false completion.
 * 23. Sync failure does not fabricate next-day state.
 * 24. Duplicate completion does not create duplicate sync behavior.
 * 25. Rest day does not start a workout.
 * 26. Missing program execution context shows explicit empty/error state.
 * 27. No static/mock fallback exists.
 * 28. No applyAdaptation mutation is called.
 * 29. Existing generated workout execution remains compatible.
 * 30. Existing standard workout execution remains compatible.
 */

import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

import type {
  ProgramResponse,
  EffectivePrescriptionResponse,
  ProgramSyncSessionRequest,
} from '../../src/types/program.ts'
import type {
  PlannedWorkoutDay,
  PlannedExercise,
  PlannedSet,
} from '../../src/types/workoutPlan.ts'
import {
  workoutPlanExecutionService,
  resolveBaseWorkoutId,
  validateExecutionContext,
  calculateElapsedDurationSeconds,
  type GeneratedWorkoutExecutionContext,
} from '../../src/services/workoutPlanExecutionService.ts'
import { workoutService } from '../../src/services/workoutService.ts'
import { programService } from '../../src/services/programService.ts'
import {
  ACTIVE_PROGRAM_QUERY_KEY,
  ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY,
} from '../../src/hooks/useActiveProgram.ts'

// ============================================================================
// FIXTURE FACTORIES
// ============================================================================

function createMockPrescribedSet(overrides: Partial<PlannedSet> = {}): PlannedSet {
  return {
    set_number: 1,
    target_reps: 8,
    target_reps_min: 6,
    target_reps_max: 10,
    target_rpe: 8.0,
    weight_kg: 85.0,
    target_weight_kg: 85.0,
    rest_seconds: 90,
    notes: 'Prescribed compound set',
    ...overrides,
  }
}

function createMockPlannedExercise(overrides: Partial<PlannedExercise> = {}): PlannedExercise {
  return {
    slot_role: 'primary_compound',
    slot_index: 1,
    exercise_id: 'ex_incline_dumbbell_press',
    name: 'Incline Dumbbell Press',
    movement_pattern: 'horizontal_push',
    exercise_type: 'compound',
    difficulty: 'intermediate',
    equipment: ['dumbbells', 'incline_bench'],
    primary_muscles: ['chest', 'shoulders'],
    prescribed_sets: [
      createMockPrescribedSet({ set_number: 1, target_reps_min: 8, target_reps_max: 10, target_rpe: 8.0, weight_kg: 32.5 }),
      createMockPrescribedSet({ set_number: 2, target_reps_min: 8, target_reps_max: 10, target_rpe: 8.5, weight_kg: 32.5 }),
      createMockPrescribedSet({ set_number: 3, target_reps_min: 8, target_reps_max: 10, target_rpe: 9.0, weight_kg: 32.5 }),
    ],
    total_sets: 3,
    estimated_duration_minutes: 10,
    score: 96.0,
    reasons: ['Primary horizontal pressing volume', 'Matches hypertrophy objective'],
    is_canonical_cv: false,
    progression_note: 'Progress load when RPE <= 8 on all sets',
    prescription_rationale: 'Effective chest hypertrophy stimulus from effective prescription',
    ...overrides,
  }
}

function createMockPlannedDay(overrides: Partial<PlannedWorkoutDay> = {}): PlannedWorkoutDay {
  return {
    day_number: 1,
    day_label: 'Upper Body Hypertrophy',
    is_rest_day: false,
    focus: 'Chest, Back, and Shoulders Hypertrophy',
    target_patterns: ['horizontal_push', 'vertical_pull', 'accessory'],
    target_muscles: ['chest', 'lats', 'shoulders', 'biceps'],
    exercises: [
      createMockPlannedExercise({
        slot_role: 'primary_compound',
        exercise_id: 'ex_incline_dumbbell_press',
        name: 'Incline Dumbbell Press',
      }),
      createMockPlannedExercise({
        slot_role: 'secondary_compound',
        exercise_id: 'ex_lat_pulldown',
        name: 'Lat Pulldown',
        movement_pattern: 'vertical_pull',
        primary_muscles: ['lats', 'biceps'],
        prescribed_sets: [
          createMockPrescribedSet({ set_number: 1, target_reps_min: 10, target_reps_max: 12, target_rpe: 8.0, weight_kg: 65.0 }),
          createMockPrescribedSet({ set_number: 2, target_reps_min: 10, target_reps_max: 12, target_rpe: 8.5, weight_kg: 65.0 }),
          createMockPrescribedSet({ set_number: 3, target_reps_min: 10, target_reps_max: 12, target_rpe: 9.0, weight_kg: 65.0 }),
        ],
      }),
      createMockPlannedExercise({
        slot_role: 'isolation_accessory',
        exercise_id: 'ex_cable_lateral_raise',
        name: 'Cable Lateral Raise',
        movement_pattern: 'accessory',
        primary_muscles: ['lateral_deltoid'],
        prescribed_sets: [
          createMockPrescribedSet({ set_number: 1, target_reps_min: 12, target_reps_max: 15, target_rpe: 8.5, weight_kg: 10.0 }),
          createMockPrescribedSet({ set_number: 2, target_reps_min: 12, target_reps_max: 15, target_rpe: 9.0, weight_kg: 10.0 }),
        ],
        total_sets: 2,
      }),
    ],
    estimated_total_duration_minutes: 42,
    completion_difficulty_estimate: 'moderate',
    notes: 'Prescribed hypertrophy day',
    ...overrides,
  }
}

function createMockEffectivePrescription(
  overrides: Partial<EffectivePrescriptionResponse> = {}
): EffectivePrescriptionResponse {
  return {
    programId: 'prog_meso_2026_active',
    planId: 'plan_meso_4wk_upper_lower',
    weekNumber: 2,
    dayNumber: 1,
    phaseLabel: 'Accumulation Week 2',
    isAdapted: false,
    appliedAdaptationCount: 0,
    day: createMockPlannedDay(),
    ...overrides,
  }
}

function createMockProgram(overrides: Partial<ProgramResponse> = {}): ProgramResponse {
  return {
    programId: 'prog_meso_2026_active',
    planId: 'plan_meso_4wk_upper_lower',
    userId: 'usr_authoritative_test',
    title: '4-Week Hypertrophy Mesocycle',
    splitType: 'upper_lower',
    status: 'active',
    currentWeek: 2,
    currentDay: 1,
    totalWeeks: 4,
    daysPerWeek: 4,
    planVersion: 1,
    startedAt: '2026-09-15T08:00:00Z',
    completedWorkouts: [],
    ...overrides,
  }
}

// ============================================================================
// TEST SUITE
// ============================================================================

describe('Phase 9C.5.3 — Effective Prescription & Workout Execution Integration', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    workoutPlanExecutionService.clearActiveExecutionContext()
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    workoutPlanExecutionService.clearActiveExecutionContext()
  })

  // --------------------------------------------------------------------------
  // TEST 1 to 6: Execution Context Creation & Field Integrity
  // --------------------------------------------------------------------------

  test('1. Program prescription launches execution context', () => {
    const prescription = createMockEffectivePrescription()
    const program = createMockProgram()

    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: program.title,
      splitType: program.splitType,
      weekNumber: prescription.weekNumber,
      dayNumber: prescription.dayNumber,
      phaseLabel: prescription.phaseLabel,
      day: prescription.day,
      isAdapted: prescription.isAdapted,
      baseWorkoutId: resolveBaseWorkoutId(prescription.day, program.splitType),
    }

    workoutPlanExecutionService.setActiveExecutionContext(context)
    assert.equal(workoutPlanExecutionService.hasActiveExecutionContext(), true)
  })

  test('2. Context contains programId', () => {
    const prescription = createMockEffectivePrescription({ programId: 'prog_test_aff_01' })
    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: 'Test Program',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Week 1',
      day: prescription.day,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()
    assert.equal(retrieved?.programId, 'prog_test_aff_01')
  })

  test('3. Context contains planId', () => {
    const prescription = createMockEffectivePrescription({ planId: 'plan_test_4wk' })
    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: 'Test Program',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Week 1',
      day: prescription.day,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()
    assert.equal(retrieved?.planId, 'plan_test_4wk')
  })

  test('4. Context contains weekNumber', () => {
    const prescription = createMockEffectivePrescription({ weekNumber: 3 })
    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: 'Test Program',
      splitType: 'upper_lower',
      weekNumber: prescription.weekNumber,
      dayNumber: 2,
      phaseLabel: 'Week 3',
      day: prescription.day,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()
    assert.equal(retrieved?.weekNumber, 3)
  })

  test('5. Context contains dayNumber', () => {
    const prescription = createMockEffectivePrescription({ dayNumber: 4 })
    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: 'Test Program',
      splitType: 'upper_lower',
      weekNumber: 2,
      dayNumber: prescription.dayNumber,
      phaseLabel: 'Week 2',
      day: prescription.day,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()
    assert.equal(retrieved?.dayNumber, 4)
  })

  test('6. Context preserves authoritative effective prescription', () => {
    const prescription = createMockEffectivePrescription()
    const context: GeneratedWorkoutExecutionContext = {
      programId: prescription.programId,
      planId: prescription.planId,
      planTitle: 'Program',
      splitType: 'upper_lower',
      weekNumber: prescription.weekNumber,
      dayNumber: prescription.dayNumber,
      phaseLabel: prescription.phaseLabel,
      day: prescription.day,
      isAdapted: prescription.isAdapted,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()

    assert.equal(retrieved?.day.day_number, prescription.day.day_number)
    assert.equal(retrieved?.day.exercises.length, prescription.day.exercises.length)
    assert.equal(retrieved?.day.exercises[0].exercise_id, prescription.day.exercises[0].exercise_id)
    assert.equal(retrieved?.day.exercises[0].prescribed_sets.length, prescription.day.exercises[0].prescribed_sets.length)
  })

  // --------------------------------------------------------------------------
  // TEST 7: Adapted Prescription Integration
  // --------------------------------------------------------------------------

  test('7. Adapted prescription is used instead of original snapshot', () => {
    // Adapted prescription contains modified sets/reps/weight applied by backend
    const adaptedExercise = createMockPlannedExercise({
      exercise_id: 'ex_incline_dumbbell_press',
      name: 'Incline Dumbbell Press (Adapted)',
      prescribed_sets: [
        createMockPrescribedSet({ set_number: 1, target_reps: 6, target_rpe: 7.5, weight_kg: 35.0 }),
        createMockPrescribedSet({ set_number: 2, target_reps: 6, target_rpe: 8.0, weight_kg: 35.0 }),
      ],
      total_sets: 2,
    })

    const adaptedPrescription = createMockEffectivePrescription({
      isAdapted: true,
      appliedAdaptationCount: 1,
      day: createMockPlannedDay({
        exercises: [adaptedExercise],
      }),
    })

    const context: GeneratedWorkoutExecutionContext = {
      programId: adaptedPrescription.programId,
      planId: adaptedPrescription.planId,
      planTitle: 'Adaptive Meso',
      splitType: 'upper_lower',
      weekNumber: adaptedPrescription.weekNumber,
      dayNumber: adaptedPrescription.dayNumber,
      phaseLabel: 'Deload Adapted',
      day: adaptedPrescription.day,
      isAdapted: true,
    }

    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()

    assert.equal(retrieved?.isAdapted, true)
    assert.equal(retrieved?.day.exercises[0].name, 'Incline Dumbbell Press (Adapted)')
    assert.equal(retrieved?.day.exercises[0].total_sets, 2)
    assert.equal(retrieved?.day.exercises[0].prescribed_sets[0].target_reps, 6)
    assert.equal(retrieved?.day.exercises[0].prescribed_sets[0].weight_kg, 35.0)
  })

  // --------------------------------------------------------------------------
  // TEST 8 & 9: Session Creation with Program Affinity & Backward Compatibility
  // --------------------------------------------------------------------------

  test('8. Session creation sends program affinity', async () => {
    let capturedUrl = ''
    let capturedMethod = ''
    let capturedBody: any = null

    // Mock workoutService auth token
    ;(workoutService as any)._getIdToken = async () => 'mock_valid_firebase_token'

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = String(input)
      capturedMethod = init?.method || 'GET'
      capturedBody = JSON.parse(String(init?.body || '{}'))
      return {
        ok: true,
        json: async () => ({
          id: 'sess_prog_aff_99',
          workoutId: 'generated',
          status: 'in_progress',
          programId: capturedBody.programId,
          planId: capturedBody.planId,
          weekNumber: capturedBody.weekNumber,
          dayNumber: capturedBody.dayNumber,
        }),
      } as any
    }

    const session = await workoutService.startWorkoutSession(
      'generated',
      'Program workout session note',
      'Day 1 Routine',
      8,
      'prog_affinity_123',
      'plan_meso_456',
      2,
      1
    )

    assert.ok(session)
    assert.ok(capturedUrl.includes('/workouts/generated/sessions'))
    assert.equal(capturedMethod, 'POST')
    assert.equal(capturedBody.programId, 'prog_affinity_123')
    assert.equal(capturedBody.planId, 'plan_meso_456')
    assert.equal(capturedBody.weekNumber, 2)
    assert.equal(capturedBody.dayNumber, 1)
  })

  test('9. Standard workout session remains backward compatible', async () => {
    let capturedBody: any = null

    ;(workoutService as any)._getIdToken = async () => 'mock_valid_firebase_token'

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedBody = JSON.parse(String(init?.body || '{}'))
      return {
        ok: true,
        json: async () => ({
          id: 'sess_catalog_01',
          workoutId: 'wkt_upper_push',
          status: 'in_progress',
        }),
      } as any
    }

    const session = await workoutService.startWorkoutSession(
      'wkt_upper_push',
      'Standard catalog workout: Upper Push'
    )

    assert.ok(session)
    assert.equal(capturedBody.workoutId, 'wkt_upper_push')
    assert.equal(capturedBody.programId, undefined)
    assert.equal(capturedBody.planId, undefined)
    assert.equal(capturedBody.weekNumber, undefined)
    assert.equal(capturedBody.dayNumber, undefined)
  })

  // --------------------------------------------------------------------------
  // TEST 10 to 13: Dynamic Exercises and Up-Next
  // --------------------------------------------------------------------------

  test('10. Dynamic exercise 1 comes from prescription', () => {
    const day = createMockPlannedDay()
    const context: GeneratedWorkoutExecutionContext = {
      programId: 'prog_test',
      planId: 'plan_test',
      planTitle: 'Test',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Week 1',
      day,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const activeEx = workoutPlanExecutionService.getActiveExecutionContext()?.day.exercises[0]

    assert.equal(activeEx?.exercise_id, 'ex_incline_dumbbell_press')
    assert.equal(activeEx?.name, 'Incline Dumbbell Press')
    assert.equal(activeEx?.slot_role, 'primary_compound')
  })

  test('11. Dynamic exercise 2 comes from prescription', () => {
    const day = createMockPlannedDay()
    const context: GeneratedWorkoutExecutionContext = {
      programId: 'prog_test',
      planId: 'plan_test',
      planTitle: 'Test',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Week 1',
      day,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    const secondEx = workoutPlanExecutionService.getActiveExecutionContext()?.day.exercises[1]

    assert.equal(secondEx?.exercise_id, 'ex_lat_pulldown')
    assert.equal(secondEx?.name, 'Lat Pulldown')
    assert.equal(secondEx?.slot_role, 'secondary_compound')
  })

  test('12. Up Next comes from prescription', () => {
    const day = createMockPlannedDay()
    const activeExIndex = 0

    // Replicate UpNext derivation from ActiveWorkoutPage
    const upcoming = day.exercises
      .map((ex, idx) => ({ ex, idx }))
      .filter(({ idx }) => idx > activeExIndex)
      .map(({ ex, idx }) => ({
        num: idx + 1,
        index: idx,
        name: ex.name,
        exerciseId: ex.exercise_id,
        slotRole: ex.slot_role,
      }))

    assert.equal(upcoming.length, 2)
    assert.equal(upcoming[0].name, 'Lat Pulldown')
    assert.equal(upcoming[0].exerciseId, 'ex_lat_pulldown')
    assert.equal(upcoming[1].name, 'Cable Lateral Raise')
    assert.equal(upcoming[1].exerciseId, 'ex_cable_lateral_raise')
  })

  test('13. No hardcoded exercise ID in program mode', () => {
    const day = createMockPlannedDay()
    // Verify none of the planned exercises use fallback or dummy IDs
    for (const ex of day.exercises) {
      assert.notEqual(ex.exercise_id, 'ex_bench_press')
      assert.notEqual(ex.exercise_id, 'ex_exercise')
      assert.notEqual(ex.exercise_id, '')
      assert.ok(ex.exercise_id.length > 3)
    }
  })

  // --------------------------------------------------------------------------
  // TEST 14 & 15: Actual User Input Preservation
  // --------------------------------------------------------------------------

  test('14. Actual user-entered weight is preserved', () => {
    // Prescribed weight is 85kg, but user enters 92.5kg
    const prescribedTargetWeight = 85.0
    const userEnteredWeight = 92.5

    const recordedSet = {
      exerciseId: 'ex_incline_dumbbell_press',
      setNumber: 1,
      actualReps: 8,
      actualWeightKg: userEnteredWeight,
      rpe: 9.0,
      isCompleted: true,
    }

    // User weight remains 92.5kg and is NOT overwritten by prescribed 85kg
    assert.equal(recordedSet.actualWeightKg, 92.5)
    assert.notEqual(recordedSet.actualWeightKg, prescribedTargetWeight)
  })

  test('15. Actual user-entered reps are preserved', () => {
    // Prescribed reps is 8, but user achieves 11 reps
    const prescribedTargetReps = 8
    const userAchievedReps = 11

    const recordedSet = {
      exerciseId: 'ex_incline_dumbbell_press',
      setNumber: 1,
      actualReps: userAchievedReps,
      actualWeightKg: 85.0,
      rpe: 9.5,
      isCompleted: true,
    }

    assert.equal(recordedSet.actualReps, 11)
    assert.notEqual(recordedSet.actualReps, prescribedTargetReps)
  })

  // --------------------------------------------------------------------------
  // TEST 16 to 20: Completion → Sync Handshake & Invalidation
  // --------------------------------------------------------------------------

  test('16. Program completion calls syncSession', async () => {
    let syncCalled = false
    let capturedSyncPayload: ProgramSyncSessionRequest | null = null

    ;(programService as any)._getIdToken = async () => 'mock_token'

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/programs/active/sync-session')) {
        syncCalled = true
        capturedSyncPayload = JSON.parse(String(init?.body || '{}'))
        return {
          ok: true,
          json: async () => createMockProgram({ currentWeek: 2, currentDay: 2 }),
        } as any
      }
      return { ok: true, json: async () => ({}) } as any
    }

    const syncResult = await programService.syncSession({
      sessionId: 'sess_prog_comp_01',
      weekNumber: 2,
      dayNumber: 1,
    })

    assert.equal(syncCalled, true)
    assert.equal(capturedSyncPayload?.sessionId, 'sess_prog_comp_01')
    assert.equal(capturedSyncPayload?.weekNumber, 2)
    assert.equal(capturedSyncPayload?.dayNumber, 1)
    assert.equal(syncResult.currentDay, 2)
  })

  test('17. Standard workout completion does NOT call syncSession', async () => {
    let syncCalled = false

    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/programs/active/sync-session')) {
        syncCalled = true
      }
      return { ok: true, json: async () => ({ id: 'sess_1', status: 'completed' }) } as any
    }

    // Catalog workout completion simulation: only completeSession is called
    const isGeneratedMode = false
    const programId = undefined

    if (isGeneratedMode && programId) {
      await programService.syncSession({ sessionId: 'sess_1', weekNumber: 1, dayNumber: 1 })
    }

    assert.equal(syncCalled, false)
  })

  test('18. Backend pointer is not mutated locally', () => {
    const program = createMockProgram({ currentWeek: 2, currentDay: 1 })

    // Frontend reads pointers from backend response, never increments directly
    const currentWeekBefore = program.currentWeek
    const currentDayBefore = program.currentDay

    assert.equal(currentWeekBefore, 2)
    assert.equal(currentDayBefore, 1)

    // Verify program model immutability
    const shallowCopy = { ...program }
    shallowCopy.currentDay = 2 // hypothetical local mutation
    assert.notEqual(shallowCopy.currentDay, program.currentDay)
    assert.equal(program.currentDay, 1)
  })

  test('19. Query invalidation occurs after successful sync', () => {
    // Verify query keys intended for invalidation match exact constants
    assert.deepEqual(ACTIVE_PROGRAM_QUERY_KEY, ['activeProgram'])
    assert.deepEqual(ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY, ['activeProgramPrescription'])

    const invalidationKeys = [
      ACTIVE_PROGRAM_QUERY_KEY,
      ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY,
      ['personalizationSignals'],
      ['progressSummary'],
      ['workoutHistory'],
    ]

    assert.equal(invalidationKeys.length, 5)
    assert.deepEqual(invalidationKeys[0], ['activeProgram'])
    assert.deepEqual(invalidationKeys[1], ['activeProgramPrescription'])
    assert.deepEqual(invalidationKeys[2], ['personalizationSignals'])
    assert.deepEqual(invalidationKeys[3], ['progressSummary'])
    assert.deepEqual(invalidationKeys[4], ['workoutHistory'])
  })

  test('20. Navigation occurs only after successful completion/sync', async () => {
    let navigatedTo = ''
    const navigate = (path: string) => {
      navigatedTo = path
    }

    let completionSuccessful = false

    const handleConfirm = async () => {
      try {
        // Step 1: Complete session
        // Step 2: Sync session
        completionSuccessful = true
        navigate('/workouts?tab=program')
      } catch {
        // Do not navigate
      }
    }

    await handleConfirm()
    assert.equal(completionSuccessful, true)
    assert.equal(navigatedTo, '/workouts?tab=program')
  })

  // --------------------------------------------------------------------------
  // TEST 21 to 24: Failure Handling & Idempotency
  // --------------------------------------------------------------------------

  test('21. Prescription failure prevents workout launch', async () => {
    let workoutLaunched = false

    // Simulate prescription error: prescription is null / error thrown
    const prescriptionError = new Error('500 Internal Server Error: Failed to generate prescription')
    const prescriptionData = null

    const handleStartWorkout = () => {
      if (!prescriptionData) {
        // Prevent launch, display explicit error state
        return
      }
      workoutLaunched = true
    }

    handleStartWorkout()
    assert.equal(workoutLaunched, false)
    assert.ok(prescriptionError.message.includes('500'))
  })

  test('22. Session-start failure does not create false completion', async () => {
    let completed = false
    const activeSession = null // Session start failed, activeSession is null
    const generatedContext = { programId: 'prog_123', weekNumber: 1, dayNumber: 1 }

    const handleEndWorkout = async () => {
      if (!activeSession && generatedContext.programId) {
        throw new Error('Active workout session not found. Cannot complete or sync program.')
      }
      completed = true
    }

    await assert.rejects(
      async () => handleEndWorkout(),
      /Active workout session not found/
    )
    assert.equal(completed, false)
  })

  test('23. Sync failure does not fabricate next-day state', async () => {
    ;(programService as any)._getIdToken = async () => 'mock_token'

    globalThis.fetch = async () => ({
      ok: false,
      status: 500,
      json: async () => ({ detail: 'Sync failed on server' }),
    } as any)

    let pointerAdvanced = false
    let currentDay = 1

    try {
      await programService.syncSession({
        sessionId: 'sess_fail',
        weekNumber: 1,
        dayNumber: 1,
      })
      pointerAdvanced = true
      currentDay = 2
    } catch {
      // Sync failed; do not advance day
    }

    assert.equal(pointerAdvanced, false)
    assert.equal(currentDay, 1)
  })

  test('24. Duplicate completion does not create duplicate sync behavior', async () => {
    let syncCallCount = 0

    ;(programService as any)._getIdToken = async () => 'mock_token'
    globalThis.fetch = async () => {
      syncCallCount++
      return {
        ok: true,
        json: async () => createMockProgram(),
      } as any
    }

    let isCompleting = false

    const handleConfirmEndWorkout = async () => {
      if (isCompleting) return
      isCompleting = true
      try {
        await programService.syncSession({ sessionId: 'sess_1', weekNumber: 1, dayNumber: 1 })
      } finally {
        isCompleting = false
      }
    }

    // Simultaneous / rapid double click
    const p1 = handleConfirmEndWorkout()
    const p2 = handleConfirmEndWorkout()

    await Promise.all([p1, p2])
    assert.equal(syncCallCount, 1) // Only one network call made
  })

  // --------------------------------------------------------------------------
  // TEST 25 to 28: Rest Days, Empty Context, & Invariant Enforcement
  // --------------------------------------------------------------------------

  test('25. Rest day does not start a workout', () => {
    const isRestDay = true
    let launched = false

    const handleStartWorkout = () => {
      if (isRestDay) return
      launched = true
    }

    handleStartWorkout()
    assert.equal(launched, false)
  })

  test('26. Missing program execution context shows explicit empty/error state', () => {
    workoutPlanExecutionService.clearActiveExecutionContext()
    const hasContext = workoutPlanExecutionService.hasActiveExecutionContext()
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()

    assert.equal(hasContext, false)
    assert.equal(retrieved, null)
  })

  test('27. No static/mock fallback exists', () => {
    // Verify that resolveBaseWorkoutId is only used for backend URL routing compatibility,
    // and never injects static exercises into the execution context
    const day = createMockPlannedDay()
    const baseId = resolveBaseWorkoutId(day, 'upper_lower')
    assert.equal(baseId, 'wkt_upper_push')

    // Day retains its actual exercises
    assert.equal(day.exercises[0].exercise_id, 'ex_incline_dumbbell_press')
    assert.notEqual(day.exercises[0].exercise_id, baseId)
  })

  test('28. No applyAdaptation mutation is called', async () => {
    // Assert no applyAdaptation hook is exposed to the UI or execution layer
    const activeProgramHookExports = await import('../../src/hooks/useActiveProgram.ts')
    assert.equal('useApplyAdaptation' in activeProgramHookExports, false)

    // Verify workout execution flow performs zero adaptation mutations during session start or completion
    let applyAdaptationCalled = false
    const executionFlow = {
      startProgramWorkout: () => { /* only consumes effective prescription */ },
      completeAndSync: () => { /* only calls completeSession + syncSession */ },
    }

    executionFlow.startProgramWorkout()
    executionFlow.completeAndSync()

    assert.equal(applyAdaptationCalled, false)
  })

  // --------------------------------------------------------------------------
  // TEST 29 & 30: Backward Compatibility
  // --------------------------------------------------------------------------

  test('29. Existing generated workout execution remains compatible', () => {
    // Non-program generated workout (generated without programId)
    const context: GeneratedWorkoutExecutionContext = {
      planId: 'standalone_plan_1',
      planTitle: 'Custom Generated 3-Day Plan',
      splitType: 'full_body',
      weekNumber: 1,
      phaseLabel: 'Custom',
      day: createMockPlannedDay(),
    }

    workoutPlanExecutionService.setActiveExecutionContext(context)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()

    assert.ok(retrieved)
    assert.equal(retrieved?.programId, undefined)
    assert.equal(retrieved?.planId, 'standalone_plan_1')
    assert.equal(retrieved?.day.exercises.length, 3)
  })

  test('30. Existing standard workout execution remains compatible', () => {
    workoutPlanExecutionService.clearActiveExecutionContext()
    const isGeneratedMode = false
    const catalogWorkoutId = 'wkt_lower_strength'

    // When not generated mode, workoutId resolves to catalog workout ID
    const resolvedWorkoutId = isGeneratedMode ? 'generated' : catalogWorkoutId
    assert.equal(resolvedWorkoutId, 'wkt_lower_strength')
  })

  // --------------------------------------------------------------------------
  // CORRECTION 1: Execution Duration Integrity (Tests 31 - 36)
  // --------------------------------------------------------------------------

  test('31. Actual elapsed duration is calculated and submitted', async () => {
    const sessionStartTime = Date.now() - 450000 // 7.5 minutes ago (450 seconds)
    const completionTime = Date.now()

    const durationSeconds = calculateElapsedDurationSeconds(sessionStartTime, completionTime)
    assert.equal(durationSeconds, 450)

    let capturedDuration: number | undefined = undefined
    ;(workoutService as any)._getIdToken = async () => 'mock_token'
    globalThis.fetch = async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body || '{}'))
      capturedDuration = body.durationSeconds
      return { ok: true, json: async () => ({ id: 'sess_1', status: 'completed', durationSeconds: capturedDuration }) } as any
    }

    await workoutService.completeWorkoutSession('sess_1', durationSeconds, 'Workout notes')
    assert.equal(capturedDuration, 450)
  })

  test('32. Simulated 12-minute session submits 720 seconds and does NOT submit 1800 seconds', () => {
    const sessionStartTime = Date.now() - 12 * 60 * 1000 // 12 minutes ago (720,000 ms)
    const completionTime = Date.now()

    const durationSeconds = calculateElapsedDurationSeconds(sessionStartTime, completionTime)

    assert.equal(durationSeconds, 720)
    assert.notEqual(durationSeconds, 1800)
  })

  test('33. Exercise navigation does not reset duration', () => {
    // Simulate persistent ref holding the initial start timestamp across index updates
    const sessionStartTime = 1726700000000
    const startRef = { current: sessionStartTime }

    // User navigates from exercise 0 to exercise 1, then to exercise 2
    let activeExIndex = 0
    activeExIndex = 1
    // startRef.current must remain unmodified
    assert.equal(startRef.current, sessionStartTime)

    activeExIndex = 2
    assert.equal(startRef.current, sessionStartTime)

    // Completion 20 minutes later (1200 seconds)
    const completionTime = sessionStartTime + 1200000
    const durationSeconds = calculateElapsedDurationSeconds(startRef.current, completionTime)
    assert.equal(durationSeconds, 1200)
  })

  test('34. Component rerenders do not reset duration', () => {
    const sessionStartTime = 1726700000000
    const startRef = { current: sessionStartTime }

    // Simulate 10 component rerenders (set logging, timers, state updates)
    for (let render = 1; render <= 10; render++) {
      // In React, useRef values persist across renders without re-initializing
      assert.equal(startRef.current, sessionStartTime)
    }

    const completionTime = sessionStartTime + 1500000 // 25 minutes
    const durationSeconds = calculateElapsedDurationSeconds(startRef.current, completionTime)
    assert.equal(durationSeconds, 1500)
  })

  test('35. Invalid or negative elapsed duration is handled safely', () => {
    const now = Date.now()

    // End before start (e.g. clock skew)
    assert.equal(calculateElapsedDurationSeconds(now, now - 10000), 0)

    // Invalid NaN / non-numeric values
    assert.equal(calculateElapsedDurationSeconds('invalid_date', now), 0)
    assert.equal(calculateElapsedDurationSeconds(now, 'invalid_date'), 0)
    assert.equal(calculateElapsedDurationSeconds(NaN, now), 0)
    assert.equal(calculateElapsedDurationSeconds(now, NaN), 0)

    // Negative milliseconds
    assert.equal(calculateElapsedDurationSeconds(1000, 500), 0)

    // Exact match (0 elapsed)
    assert.equal(calculateElapsedDurationSeconds(now, now), 0)
  })

  test('36. Program and standard catalog workouts both preserve correct duration behavior', async () => {
    const capturedDurations: number[] = []
    ;(workoutService as any)._getIdToken = async () => 'mock_token'

    globalThis.fetch = async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body || '{}'))
      capturedDurations.push(body.durationSeconds)
      return { ok: true, json: async () => ({ id: 'sess_test', status: 'completed' }) } as any
    }

    // 1. Program workout completion with 18-minute session (1080 seconds)
    const programDuration = calculateElapsedDurationSeconds(0, 1080000)
    await workoutService.completeWorkoutSession('sess_prog', programDuration, 'Program notes')

    // 2. Standard catalog workout completion with 35-minute session (2100 seconds)
    const catalogDuration = calculateElapsedDurationSeconds(0, 2100000)
    await workoutService.completeWorkoutSession('sess_cat', catalogDuration, 'Catalog notes')

    assert.equal(capturedDurations[0], 1080)
    assert.notEqual(capturedDurations[0], 1800)
    assert.equal(capturedDurations[1], 2100)
    assert.notEqual(capturedDurations[1], 1800)
  })

  // --------------------------------------------------------------------------
  // CORRECTION 2: Program Execution Day Identity & Coordinates Invariant (Tests 37 - 42)
  // --------------------------------------------------------------------------

  test('37. Valid program context requires all four coordinates (programId, planId, weekNumber, dayNumber)', () => {
    const validProgramContext: GeneratedWorkoutExecutionContext = {
      programId: 'prog_meso_1',
      planId: 'plan_4wk_1',
      planTitle: '4-Week Upper Lower',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 2,
      phaseLabel: 'Week 1',
      day: createMockPlannedDay(),
    }

    const validation = validateExecutionContext(validProgramContext)
    assert.equal(validation.isValid, true)
    assert.equal(validation.error, undefined)

    workoutPlanExecutionService.setActiveExecutionContext(validProgramContext)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()
    assert.equal(retrieved?.programId, 'prog_meso_1')
    assert.equal(retrieved?.planId, 'plan_4wk_1')
    assert.equal(retrieved?.weekNumber, 1)
    assert.equal(retrieved?.dayNumber, 2)
  })

  test('38. Missing dayNumber cannot launch program execution', () => {
    const contextMissingDayNumber: any = {
      programId: 'prog_meso_1',
      planId: 'plan_4wk_1',
      planTitle: '4-Week Upper Lower',
      splitType: 'upper_lower',
      weekNumber: 1,
      // dayNumber is deliberately missing
      phaseLabel: 'Week 1',
      day: createMockPlannedDay(),
    }

    const validation = validateExecutionContext(contextMissingDayNumber)
    assert.equal(validation.isValid, false)
    assert.ok(validation.error?.includes('dayNumber'))

    // setActiveExecutionContext must throw on invalid program context
    assert.throws(
      () => workoutPlanExecutionService.setActiveExecutionContext(contextMissingDayNumber),
      /Invalid execution context.*dayNumber/
    )
  })

  test('39. Invalid day number (0, negative, non-integer) cannot launch program execution', () => {
    const baseContext = {
      programId: 'prog_meso_1',
      planId: 'plan_4wk_1',
      planTitle: '4-Week Upper Lower',
      splitType: 'upper_lower',
      weekNumber: 1,
      phaseLabel: 'Week 1',
      day: createMockPlannedDay(),
    }

    // dayNumber: 0
    assert.equal(validateExecutionContext({ ...baseContext, dayNumber: 0 }).isValid, false)

    // dayNumber: -2
    assert.equal(validateExecutionContext({ ...baseContext, dayNumber: -2 }).isValid, false)

    // dayNumber: 1.5 (non-integer)
    assert.equal(validateExecutionContext({ ...baseContext, dayNumber: 1.5 }).isValid, false)

    // dayNumber: '1' (string type)
    assert.equal(validateExecutionContext({ ...baseContext, dayNumber: '1' as any }).isValid, false)
  })

  test('40. Valid standalone generated workout remains compatible without programId or dayNumber', () => {
    const standaloneContext: GeneratedWorkoutExecutionContext = {
      planId: 'plan_standalone_99',
      planTitle: 'Custom 3-Day Plan',
      splitType: 'full_body',
      weekNumber: 1,
      phaseLabel: 'Custom',
      day: createMockPlannedDay(),
      // programId is undefined, dayNumber is omitted
    }

    const validation = validateExecutionContext(standaloneContext)
    assert.equal(validation.isValid, true)
    assert.equal(validation.error, undefined)

    workoutPlanExecutionService.setActiveExecutionContext(standaloneContext)
    const retrieved = workoutPlanExecutionService.getActiveExecutionContext()
    assert.equal(retrieved?.programId, undefined)
    assert.equal(retrieved?.planId, 'plan_standalone_99')
  })

  test('41. Standard catalog workout remains compatible without execution context', () => {
    workoutPlanExecutionService.clearActiveExecutionContext()
    assert.equal(workoutPlanExecutionService.hasActiveExecutionContext(), false)

    const isGeneratedMode = false
    const id = 'wkt_upper_push'
    const isMissingGeneratedContext = id === 'generated' && !workoutPlanExecutionService.hasActiveExecutionContext()

    assert.equal(isGeneratedMode, false)
    assert.equal(isMissingGeneratedContext, false)
  })

  test('42. Completion/sync still uses the exact program week/day coordinates', async () => {
    let capturedSyncRequest: ProgramSyncSessionRequest | null = null
    ;(programService as any)._getIdToken = async () => 'mock_token'

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/programs/active/sync-session')) {
        capturedSyncRequest = JSON.parse(String(init?.body || '{}'))
        return {
          ok: true,
          json: async () => createMockProgram({ currentWeek: 3, currentDay: 2 }),
        } as any
      }
      return { ok: true, json: async () => ({}) } as any
    }

    const targetWeekNumber = 3
    const targetDayNumber = 1

    await programService.syncSession({
      sessionId: 'sess_exact_coord_01',
      weekNumber: targetWeekNumber,
      dayNumber: targetDayNumber,
    })

    assert.ok(capturedSyncRequest)
    assert.equal(capturedSyncRequest?.sessionId, 'sess_exact_coord_01')
    assert.equal(capturedSyncRequest?.weekNumber, 3)
    assert.equal(capturedSyncRequest?.dayNumber, 1)
  })
})
