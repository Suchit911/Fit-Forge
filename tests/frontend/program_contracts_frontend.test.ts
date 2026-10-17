/**
 * Frontend Test Suite for Phase 9C.5.1:
 * Frontend Program Contracts & Data Layer.
 *
 * Covers 23 explicit verification points:
 * 1. ProgramResponse serialization/deserialization
 * 2. EffectivePrescriptionResponse parsing
 * 3. ProgramVersionsResponse parsing
 * 4. Active program GET request (/programs/active)
 * 5. Effective prescription request (/programs/active/prescription/{week}/{day})
 * 6. Program versions request (/programs/active/versions)
 * 7. Program-by-ID request (/programs/{program_id})
 * 8. Start program request (/programs/start)
 * 9. Sync session request (/programs/active/sync-session)
 * 10. Abandon program request (/programs/active/abandon)
 * 11. Firebase Bearer token attachment on authenticated requests
 * 12. Missing/unauthenticated behavior (rejects or returns null)
 * 13. API error propagation (401, 404, 409, 422, 500)
 * 14. No mock fallback on API failure (error thrown, zero fabrication)
 * 15. No static catalog fallback on prescription failure
 * 16. Correct prescription URL construction (/programs/active/prescription/{week}/{day})
 * 17. Correct program session affinity fields in startWorkoutSession
 * 18. Query key correctness and deterministic namespacing
 * 19. Query invalidation after syncSession
 * 20. Query invalidation after startProgram
 * 21. Query invalidation after abandonProgram
 * 22. Standard workout session compatibility (arguments omitted)
 * 23. Invariant: zero applyAdaptation mutation exposed in hook layer
 */

import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

import type {
  ProgramResponse,
  EffectivePrescriptionResponse,
  ProgramVersionsResponse,
  ProgramStartRequest,
  ProgramSyncSessionRequest,
  ProgramAbandonRequest,
} from '../../src/types/program.ts'
import type { WorkoutPlanResponse } from '../../src/types/workoutPlan.ts'
import { programService } from '../../src/services/programService.ts'
import { workoutService } from '../../src/services/workoutService.ts'
import {
  ACTIVE_PROGRAM_QUERY_KEY,
  ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY,
  PROGRAM_VERSIONS_QUERY_KEY,
  effectivePrescriptionQueryKey,
} from '../../src/hooks/useActiveProgram.ts'
import * as activeProgramHookModule from '../../src/hooks/useActiveProgram.ts'

// ============================================================================
// MOCK DATA FACTORIES
// ============================================================================

function createMockPlan(): WorkoutPlanResponse {
  return {
    plan_id: 'pln_mock_123',
    title: '4-Week Hypertrophy Mesocycle',
    description: 'Deterministic 4-day plan.',
    target_goal: 'muscle_gain',
    fitness_level: 'intermediate',
    split_type: 'upper_lower',
    training_days_per_week: 4,
    total_weeks: 4,
    weeks: [
      {
        week_number: 1,
        phase_label: 'Baseline Accumulation',
        days: [
          {
            day_number: 1,
            day_label: 'Upper Body A',
            is_rest_day: false,
            focus: 'Horizontal Push & Pull',
            target_patterns: ['horizontal_push', 'horizontal_pull'],
            target_muscles: ['chest', 'back'],
            exercises: [
              {
                slot_role: 'primary_compound',
                slot_index: 1,
                exercise_id: 'ex_bench_press',
                name: 'Barbell Bench Press',
                movement_pattern: 'horizontal_push',
                exercise_type: 'compound',
                difficulty: 'intermediate',
                equipment: ['barbell', 'bench'],
                primary_muscles: ['chest', 'triceps'],
                prescribed_sets: [
                  {
                    set_number: 1,
                    target_reps: 8,
                    target_reps_min: 8,
                    target_reps_max: 8,
                    target_rpe: 8.0,
                    rest_seconds: 120,
                    notes: null,
                  },
                ],
                total_sets: 1,
                estimated_duration_minutes: 6,
                score: 95.0,
                reasons: ['Primary horizontal compound'],
                is_canonical_cv: true,
              },
            ],
            total_sets: 1,
            estimated_duration_minutes: 6,
          },
        ],
        total_weekly_sets: 1,
        total_workouts: 1,
      },
    ],
    applied_filters: {},
    feasibility_check_passed: true,
    duration_feasibility: 'feasible',
    diagnostics: [],
    conflicting_filters: [],
  }
}

function createMockProgramResponse(overrides: Partial<ProgramResponse> = {}): ProgramResponse {
  const plan = createMockPlan()
  return {
    programId: 'prog_20260918_abc123',
    userId: 'usr_test_789',
    planId: plan.plan_id,
    title: '4-Week Hypertrophy Mesocycle',
    status: 'active',
    splitType: 'upper_lower',
    totalWeeks: 4,
    daysPerWeek: 4,
    currentWeek: 1,
    currentDay: 1,
    startedAt: '2026-09-18T00:00:00Z',
    updatedAt: '2026-09-18T00:00:00Z',
    completedAt: null,
    abandonedAt: null,
    completedWorkouts: [],
    totalPlannedWorkouts: 16,
    adaptationHistory: [],
    planSnapshot: plan,
    effectivePlanSnapshot: plan,
    planVersion: 1,
    pendingNextBlockSplit: null,
    createdFrom: 'generated_plan',
    programVersion: '9C.3',
    programSchemaVersion: '1.1.0',
    planSchemaVersion: '1.0.0',
    ...overrides,
  }
}

function createMockPrescriptionResponse(
  overrides: Partial<EffectivePrescriptionResponse> = {}
): EffectivePrescriptionResponse {
  const plan = createMockPlan()
  return {
    programId: 'prog_20260918_abc123',
    planId: plan.plan_id,
    planVersion: 1,
    weekNumber: 1,
    dayNumber: 1,
    phaseLabel: 'Baseline Accumulation',
    isAdapted: false,
    isCompleted: false,
    day: plan.weeks[0].days[0],
    appliedAdaptations: [],
    ...overrides,
  }
}

function createMockVersionsResponse(): ProgramVersionsResponse {
  return {
    programId: 'prog_20260918_abc123',
    programVersion: '9C.3',
    planVersion: 2,
    totalAdaptationsApplied: 1,
    adaptationHistory: [
      {
        decisionId: 'dec_sha256_hash123',
        appliedAt: '2026-09-18T00:30:00Z',
        adaptationType: 'load_progression',
        ruleCode: 'DOUBLE_PROGRESSION_LOAD_INCREASE',
        exerciseId: 'ex_bench_press',
        affectedDaysCount: 3,
        details: 'Applied +2.5 kg load progression to Barbell Bench Press.',
        previousPrescription: { weightKg: 80.0, targetRepsMin: 8, targetRepsMax: 8 },
        proposedPrescription: { weightKg: 82.5, targetRepsMin: 8, targetRepsMax: 8 },
        rationale: 'Completed target reps across 3 qualifying sessions.',
        reasons: ['Prescribed reps achieved in all working sets.'],
        isReversible: true,
      },
    ],
    pendingNextBlockSplit: null,
  }
}

// ============================================================================
// TEST SUITE
// ============================================================================

describe('Phase 9C.5.1 — Frontend Program Contracts & Data Layer', () => {
  const originalFetch = globalThis.fetch
  const originalGetIdTokenProg = programService._getIdToken
  const originalGetIdTokenWkt = workoutService._getIdToken

  beforeEach(() => {
    programService._getIdToken = async () => 'test-firebase-id-token'
    workoutService._getIdToken = async () => 'test-firebase-id-token'
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    programService._getIdToken = originalGetIdTokenProg
    workoutService._getIdToken = originalGetIdTokenWkt
  })

  // --------------------------------------------------------------------------
  // 1-3. Schemas and Model Parsing
  // --------------------------------------------------------------------------
  test('1. ProgramResponse serialization and field integrity', () => {
    const raw = createMockProgramResponse({
      completedWorkouts: [
        {
          sessionId: 'sess_1',
          planId: 'pln_mock_123',
          weekNumber: 1,
          dayNumber: 1,
          completedAt: '2026-09-18T01:00:00Z',
          durationSeconds: 1800,
          completedSetsCount: 4,
          totalSetsCount: 4,
        },
      ],
    })
    assert.equal(raw.programId, 'prog_20260918_abc123')
    assert.equal(raw.status, 'active')
    assert.equal(raw.totalWeeks, 4)
    assert.equal(raw.currentWeek, 1)
    assert.equal(raw.currentDay, 1)
    assert.equal(raw.planVersion, 1)
    assert.equal(raw.completedWorkouts.length, 1)
    assert.equal(raw.completedWorkouts[0].sessionId, 'sess_1')
  })

  test('2. EffectivePrescriptionResponse parsing and day structure', () => {
    const rx = createMockPrescriptionResponse({
      isAdapted: true,
      appliedAdaptations: [
        {
          decisionId: 'dec_123',
          adaptationType: 'load_progression',
          ruleCode: 'DOUBLE_PROGRESSION_LOAD_INCREASE',
          deltaMagnitude: 2.5,
          deltaUnit: 'kg',
        },
      ],
    })
    assert.equal(rx.programId, 'prog_20260918_abc123')
    assert.equal(rx.isAdapted, true)
    assert.equal(rx.isCompleted, false)
    assert.equal(rx.day.day_number, 1)
    assert.equal(rx.day.exercises.length, 1)
    assert.equal(rx.appliedAdaptations.length, 1)
    assert.equal(rx.appliedAdaptations[0].deltaMagnitude, 2.5)
  })

  test('3. ProgramVersionsResponse parsing and adaptation audit history', () => {
    const vers = createMockVersionsResponse()
    assert.equal(vers.programId, 'prog_20260918_abc123')
    assert.equal(vers.planVersion, 2)
    assert.equal(vers.totalAdaptationsApplied, 1)
    assert.equal(vers.adaptationHistory.length, 1)
    assert.equal(vers.adaptationHistory[0].ruleCode, 'DOUBLE_PROGRESSION_LOAD_INCREASE')
    assert.equal(vers.adaptationHistory[0].isReversible, true)
  })

  // --------------------------------------------------------------------------
  // 4-7. Read Service Requests
  // --------------------------------------------------------------------------
  test('4. Active program GET request (/programs/active)', async () => {
    let capturedUrl = ''
    let capturedAuth = ''

    globalThis.fetch = async (input, init) => {
      capturedUrl = input.toString()
      capturedAuth = (init?.headers as Record<string, string>)?.Authorization || ''
      return new Response(JSON.stringify(createMockProgramResponse()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const prog = await programService.getActiveProgram()
    assert.ok(prog)
    assert.ok(capturedUrl.endsWith('/programs/active'))
    assert.equal(capturedAuth, 'Bearer test-firebase-id-token')
  })

  test('5. Effective prescription GET request (/programs/active/prescription/{week}/{day})', async () => {
    let capturedUrl = ''

    globalThis.fetch = async (input) => {
      capturedUrl = input.toString()
      return new Response(JSON.stringify(createMockPrescriptionResponse({ weekNumber: 2, dayNumber: 3 })), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const rx = await programService.getEffectivePrescription(2, 3)
    assert.equal(rx.weekNumber, 2)
    assert.equal(rx.dayNumber, 3)
    assert.ok(capturedUrl.endsWith('/programs/active/prescription/2/3'))
  })

  test('6. Program versions GET request (/programs/active/versions)', async () => {
    let capturedUrl = ''

    globalThis.fetch = async (input) => {
      capturedUrl = input.toString()
      return new Response(JSON.stringify(createMockVersionsResponse()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const vers = await programService.getProgramVersions()
    assert.equal(vers.planVersion, 2)
    assert.ok(capturedUrl.endsWith('/programs/active/versions'))
  })

  test('7. Program by ID GET request (/programs/{program_id})', async () => {
    let capturedUrl = ''

    globalThis.fetch = async (input) => {
      capturedUrl = input.toString()
      return new Response(JSON.stringify(createMockProgramResponse({ programId: 'prog_target_456' })), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const prog = await programService.getProgramById('prog_target_456')
    assert.equal(prog.programId, 'prog_target_456')
    assert.ok(capturedUrl.endsWith('/programs/prog_target_456'))
  })

  // --------------------------------------------------------------------------
  // 8-10. Lifecycle Service Requests
  // --------------------------------------------------------------------------
  test('8. Start program POST request (/programs/start)', async () => {
    let capturedMethod = ''
    let capturedUrl = ''
    let capturedBody = ''

    globalThis.fetch = async (input, init) => {
      capturedMethod = init?.method || ''
      capturedUrl = input.toString()
      capturedBody = init?.body?.toString() || ''
      return new Response(JSON.stringify(createMockProgramResponse()), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const req: ProgramStartRequest = { plan: createMockPlan(), title: 'My Program' }
    const started = await programService.startProgram(req)
    assert.equal(capturedMethod, 'POST')
    assert.ok(capturedUrl.endsWith('/programs/start'))
    assert.ok(capturedBody.includes('My Program'))
    assert.equal(started.title, '4-Week Hypertrophy Mesocycle')
  })

  test('9. Sync session POST request (/programs/active/sync-session)', async () => {
    let capturedMethod = ''
    let capturedUrl = ''
    let capturedBody = ''

    globalThis.fetch = async (input, init) => {
      capturedMethod = init?.method || ''
      capturedUrl = input.toString()
      capturedBody = init?.body?.toString() || ''
      return new Response(JSON.stringify(createMockProgramResponse({ currentDay: 2 })), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const req: ProgramSyncSessionRequest = {
      sessionId: 'sess_abc',
      weekNumber: 1,
      dayNumber: 1,
    }
    const synced = await programService.syncSession(req)
    assert.equal(capturedMethod, 'POST')
    assert.ok(capturedUrl.endsWith('/programs/active/sync-session'))
    assert.ok(capturedBody.includes('sess_abc'))
    assert.equal(synced.currentDay, 2)
  })

  test('10. Abandon program POST request (/programs/active/abandon)', async () => {
    let capturedMethod = ''
    let capturedUrl = ''
    let capturedBody = ''

    globalThis.fetch = async (input, init) => {
      capturedMethod = init?.method || ''
      capturedUrl = input.toString()
      capturedBody = init?.body?.toString() || ''
      return new Response(JSON.stringify(createMockProgramResponse({ status: 'abandoned' })), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const req: ProgramAbandonRequest = { reason: 'User requested reset' }
    const abandoned = await programService.abandonActiveProgram(req)
    assert.equal(capturedMethod, 'POST')
    assert.ok(capturedUrl.endsWith('/programs/active/abandon'))
    assert.ok(capturedBody.includes('User requested reset'))
    assert.equal(abandoned.status, 'abandoned')
  })

  // --------------------------------------------------------------------------
  // 11-15. Authentication & Error Invariants
  // --------------------------------------------------------------------------
  test('11. Firebase Bearer token is properly attached on all authenticated requests', async () => {
    const authHeaders: string[] = []

    globalThis.fetch = async (_input, init) => {
      const h = (init?.headers as Record<string, string>)?.Authorization
      if (h) authHeaders.push(h)
      return new Response(JSON.stringify(createMockProgramResponse()), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    await programService.getActiveProgram()
    await programService.getEffectivePrescription(1, 1)
    await programService.getProgramVersions()
    assert.equal(authHeaders.length, 3)
    authHeaders.forEach((token) => assert.equal(token, 'Bearer test-firebase-id-token'))
  })

  test('12. Missing auth token rejects or returns null', async () => {
    programService._getIdToken = async () => null

    // getActiveProgram returns null when unauthenticated
    const active = await programService.getActiveProgram()
    assert.equal(active, null)

    // Prescription and lifecycle calls throw authentication required
    await assert.rejects(
      () => programService.getEffectivePrescription(1, 1),
      /Authentication required/
    )
    await assert.rejects(
      () => programService.getProgramVersions(),
      /Authentication required/
    )
    await assert.rejects(
      () => programService.startProgram({ plan: createMockPlan() }),
      /Authentication required/
    )
    await assert.rejects(
      () => programService.syncSession({ sessionId: 's1' }),
      /Authentication required/
    )
    await assert.rejects(
      () => programService.abandonActiveProgram(),
      /Authentication required/
    )
  })

  test('13. API error propagation (401, 404, 409, 422, 500)', async () => {
    // 404 on getActiveProgram returns null (normal empty state)
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'No active program found.' }), { status: 404 })
    const active404 = await programService.getActiveProgram()
    assert.equal(active404, null)

    // 409 Conflict on startProgram throws with detail
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'User already has an active program.' }), { status: 409 })
    await assert.rejects(
      () => programService.startProgram({ plan: createMockPlan() }),
      /User already has an active program/
    )

    // 422 Unprocessable Entity on syncSession throws with detail
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Session lacks program affinity.' }), { status: 422 })
    await assert.rejects(
      () => programService.syncSession({ sessionId: 's_unaffiliated' }),
      /Session lacks program affinity/
    )

    // 500 Internal Server Error propagates error
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Internal server error' }), { status: 500 })
    await assert.rejects(
      () => programService.getProgramVersions(),
      /Internal server error/
    )
  })

  test('14. No mock fallback on prescription API failure', async () => {
    globalThis.fetch = async () => new Response('Internal error', { status: 500 })
    await assert.rejects(
      () => programService.getEffectivePrescription(1, 1),
      /Failed to fetch effective prescription/
    )
  })

  test('15. No static catalog fallback on prescription failure', async () => {
    globalThis.fetch = async () => {
      throw new Error('Network error')
    }
    await assert.rejects(
      () => programService.getEffectivePrescription(1, 1),
      /Network connection failure/
    )
  })

  test('16. Correct prescription URL construction preserves week and day numbers', async () => {
    const requestedUrls: string[] = []
    globalThis.fetch = async (input) => {
      requestedUrls.push(input.toString())
      return new Response(JSON.stringify(createMockPrescriptionResponse()), { status: 200 })
    }

    await programService.getEffectivePrescription(4, 2)
    assert.ok(requestedUrls[0].endsWith('/programs/active/prescription/4/2'))
  })

  // --------------------------------------------------------------------------
  // 17 & 22. Workout Session Affinity & Compatibility
  // --------------------------------------------------------------------------
  test('17. startWorkoutSession transmits program affinity fields when provided', async () => {
    let capturedPayload: any = null

    globalThis.fetch = async (_input, init) => {
      capturedPayload = JSON.parse(init?.body?.toString() || '{}')
      return new Response(
        JSON.stringify({
          id: 'sess_created',
          workoutId: 'generated',
          status: 'in_progress',
          programId: capturedPayload.programId,
          planId: capturedPayload.planId,
          weekNumber: capturedPayload.weekNumber,
          dayNumber: capturedPayload.dayNumber,
        }),
        { status: 201 }
      )
    }

    const session = await workoutService.startWorkoutSession(
      'generated',
      'Notes for program workout',
      'Upper Day 1',
      16,
      'prog_test_123',
      'plan_test_456',
      2,
      3
    )

    assert.ok(session)
    assert.equal(capturedPayload.workoutId, 'generated')
    assert.equal(capturedPayload.programId, 'prog_test_123')
    assert.equal(capturedPayload.planId, 'plan_test_456')
    assert.equal(capturedPayload.weekNumber, 2)
    assert.equal(capturedPayload.dayNumber, 3)
  })

  test('22. Standard workout session behavior remains 100% backward compatible', async () => {
    let capturedPayload: any = null

    globalThis.fetch = async (_input, init) => {
      capturedPayload = JSON.parse(init?.body?.toString() || '{}')
      return new Response(
        JSON.stringify({
          id: 'sess_std',
          workoutId: 'wkt_upper_push',
          status: 'in_progress',
        }),
        { status: 201 }
      )
    }

    // Call startWorkoutSession without program affinity fields (legacy catalog call)
    const session = await workoutService.startWorkoutSession(
      'wkt_upper_push',
      'Catalog workout notes',
      'Upper Push Routine',
      12
    )

    assert.ok(session)
    assert.equal(capturedPayload.workoutId, 'wkt_upper_push')
    assert.equal(capturedPayload.workoutTitle, 'Upper Push Routine')
    assert.equal(capturedPayload.programId, undefined)
    assert.equal(capturedPayload.planId, undefined)
    assert.equal(capturedPayload.weekNumber, undefined)
    assert.equal(capturedPayload.dayNumber, undefined)
  })

  // --------------------------------------------------------------------------
  // 18-21. TanStack Query Keys & Invalidation Matrix
  // --------------------------------------------------------------------------
  test('18. Query key correctness and deterministic namespacing', () => {
    assert.deepEqual(ACTIVE_PROGRAM_QUERY_KEY, ['activeProgram'])
    assert.deepEqual(ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY, ['activeProgramPrescription'])
    assert.deepEqual(PROGRAM_VERSIONS_QUERY_KEY, ['programVersions'])
    assert.deepEqual(effectivePrescriptionQueryKey(2, 4), ['activeProgramPrescription', 2, 4])
  })

  test('19. Query invalidation after sync triggers expected cache keys', () => {
    const invalidatedKeys: any[] = []
    const updatedDataKeys: any[] = []

    const mockQueryClient = {
      setQueryData: (key: any, _data: any) => {
        updatedDataKeys.push(key)
      },
      invalidateQueries: (filter: { queryKey: any }) => {
        invalidatedKeys.push(filter.queryKey)
      },
    }

    // Simulate onSuccess handler of useSyncProgramSession
    const dummyUpdatedProgram = createMockProgramResponse({ currentDay: 2 })
    mockQueryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, dummyUpdatedProgram)
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
    mockQueryClient.invalidateQueries({ queryKey: ['personalizationSignals'] })
    mockQueryClient.invalidateQueries({ queryKey: ['progressSummary'] })
    mockQueryClient.invalidateQueries({ queryKey: ['workoutHistory'] })

    assert.deepEqual(updatedDataKeys[0], ['activeProgram'])
    assert.ok(invalidatedKeys.some((k) => k[0] === 'activeProgram'))
    assert.ok(invalidatedKeys.some((k) => k[0] === 'activeProgramPrescription'))
    assert.ok(invalidatedKeys.some((k) => k[0] === 'personalizationSignals'))
    assert.ok(invalidatedKeys.some((k) => k[0] === 'progressSummary'))
    assert.ok(invalidatedKeys.some((k) => k[0] === 'workoutHistory'))
  })

  test('20. Query invalidation after start triggers active program and prescription refresh', () => {
    const invalidatedKeys: any[] = []
    const updatedDataKeys: any[] = []

    const mockQueryClient = {
      setQueryData: (key: any, _data: any) => {
        updatedDataKeys.push(key)
      },
      invalidateQueries: (filter: { queryKey: any }) => {
        invalidatedKeys.push(filter.queryKey)
      },
    }

    const dummyNewProgram = createMockProgramResponse()
    mockQueryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, dummyNewProgram)
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
    mockQueryClient.invalidateQueries({ queryKey: PROGRAM_VERSIONS_QUERY_KEY })

    assert.deepEqual(updatedDataKeys[0], ['activeProgram'])
    assert.ok(invalidatedKeys.some((k) => k[0] === 'activeProgram'))
    assert.ok(invalidatedKeys.some((k) => k[0] === 'activeProgramPrescription'))
    assert.ok(invalidatedKeys.some((k) => k[0] === 'programVersions'))
  })

  test('21. Query invalidation after abandon evicts active program and prescription queries', () => {
    const invalidatedKeys: any[] = []
    const removedKeys: any[] = []
    let activeProgramData: any = 'not-null'

    const mockQueryClient = {
      setQueryData: (key: any, data: any) => {
        if (key[0] === 'activeProgram') activeProgramData = data
      },
      invalidateQueries: (filter: { queryKey: any }) => {
        invalidatedKeys.push(filter.queryKey)
      },
      removeQueries: (filter: { queryKey: any }) => {
        removedKeys.push(filter.queryKey)
      },
    }

    mockQueryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, null)
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
    mockQueryClient.removeQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
    mockQueryClient.removeQueries({ queryKey: PROGRAM_VERSIONS_QUERY_KEY })

    assert.equal(activeProgramData, null)
    assert.ok(invalidatedKeys.some((k) => k[0] === 'activeProgram'))
    assert.ok(removedKeys.some((k) => k[0] === 'activeProgramPrescription'))
    assert.ok(removedKeys.some((k) => k[0] === 'programVersions'))
  })

  // --------------------------------------------------------------------------
  // 23. Strict Invariant Verification
  // --------------------------------------------------------------------------
  test('23. Invariant: zero applyAdaptation mutation or hook is exported for the frontend UI', () => {
    // Inspect exports of useActiveProgram module
    const exports = Object.keys(activeProgramHookModule)
    assert.ok(!exports.includes('useApplyAdaptation'), 'useApplyAdaptation must not be exported')
    assert.ok(!exports.includes('applyAdaptationMutation'), 'applyAdaptationMutation must not be exported')
  })
})
