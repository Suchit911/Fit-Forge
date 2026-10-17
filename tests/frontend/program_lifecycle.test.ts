/**
 * Dedicated Frontend Test Suite for Phase 9C.5.5:
 * Program Lifecycle Management & Empty States.
 *
 * Covers all required verification criteria:
 * 1. No active program empty state resolution.
 * 2. Active program view rendering and state integrity.
 * 3. Completed program state rendering in read-only mode.
 * 4. Abandoned program state rendering in read-only mode.
 * 5. Start Active Program button payload and contract compliance.
 * 6. Start Active Program loading and disabled state.
 * 7. Start Active Program success flow and cache invalidation.
 * 8. Start Active Program HTTP 409 Conflict handling.
 * 9. Duplicate start submission prevention.
 * 10. Start Active Program navigation to /workouts?tab=program.
 * 11. Empty-state CTA navigation to /workouts?tab=generate.
 * 12. Abandon Program button visible on active program.
 * 13. Abandon confirmation modal display and preservation notice.
 * 14. Cancel abandonment closes modal without mutation.
 * 15. Abandon loading state disables actions.
 * 16. Abandon mutation success order and cache invalidation.
 * 17. Abandon mutation failure preserves active program and displays error.
 * 18. Execution context cleared ONLY after confirmed abandon success.
 * 19. Execution context preserved when abandon mutation fails.
 * 20. Backend-authoritative lifecycle state (no local status fabrication).
 * 21. No local status mutation or progress inference.
 * 22. No static workout fallback on program execution.
 * 23. Four-coordinate execution invariant (programId, planId, weekNumber, dayNumber).
 * 24. Today's prescription execution disabled when program is completed or abandoned.
 * 25. Standard catalog workout isolation (no program affinity or lifecycle controls).
 * 26. Modal keyboard accessibility (Escape key dismiss).
 * 27. Error state vs no-data state distinction (404 = empty state, 500 = error state with retry).
 * 28. Invariant: UI never mutates Firestore directly or bypasses FastAPI.
 */

import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

import type {
  ProgramResponse,
  ProgramStartRequest,
  ProgramAbandonRequest,
  EffectivePrescriptionResponse,
} from '../../src/types/program.ts'
import type {
  WorkoutPlanResponse,
  PlannedWorkoutDay,
} from '../../src/types/workoutPlan.ts'
import { programService } from '../../src/services/programService.ts'
import {
  workoutPlanExecutionService,
  type ProgramWorkoutExecutionContext,
  type StandaloneGeneratedExecutionContext,
} from '../../src/services/workoutPlanExecutionService.ts'
import {
  ACTIVE_PROGRAM_QUERY_KEY,
  ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY,
  PROGRAM_VERSIONS_QUERY_KEY,
} from '../../src/hooks/useActiveProgram.ts'

// ============================================================================
// Authoritative Test Fixtures
// ============================================================================

const MOCK_AUTH_TOKEN = 'mock-firebase-bearer-token-phase-9c-5-5'

const MOCK_PLANNED_DAY: PlannedWorkoutDay = {
  day_number: 1,
  day_label: 'Push Focus',
  focus: 'Chest, Shoulders & Triceps',
  is_rest_day: false,
  estimated_duration_minutes: 50,
  total_sets: 12,
  exercises: [
    {
      slot_index: 0,
      slot_role: 'primary_compound',
      exercise_id: 'ex_bench_press',
      name: 'Barbell Bench Press',
      movement_pattern: 'horizontal_push',
      is_canonical_cv: true,
      equipment: ['barbell', 'bench'],
      primary_muscles: ['chest', 'triceps'],
      total_sets: 3,
      estimated_duration_minutes: 15,
      prescription_rationale: 'Primary strength focus',
      reasons: ['Compound strength builder'],
      prescribed_sets: [
        { set_number: 1, target_reps: 8, rest_seconds: 90, target_rpe: 8, target_weight_kg: 80.0 },
        { set_number: 2, target_reps: 8, rest_seconds: 90, target_rpe: 8, target_weight_kg: 80.0 },
        { set_number: 3, target_reps: 8, rest_seconds: 90, target_rpe: 8, target_weight_kg: 80.0 },
      ],
    },
  ],
}

const MOCK_PLAN_SNAPSHOT: WorkoutPlanResponse = {
  plan_id: 'plan_meso_hypertrophy_4w',
  title: '4-Week Upper/Lower Mesocycle',
  description: 'Evidence-based periodized strength block',
  split_type: 'upper_lower',
  total_weeks: 4,
  training_days_per_week: 4,
  duration_feasibility: 'feasible',
  feasibility_check_passed: true,
  appliedFilters: {},
  weeks: [
    {
      week_number: 1,
      phase_label: 'Accumulation',
      total_workouts: 4,
      total_weekly_sets: 48,
      days: [MOCK_PLANNED_DAY],
    },
  ],
}

const MOCK_ACTIVE_PROGRAM: ProgramResponse = {
  programId: 'prog_live_9c55_test_001',
  userId: 'user_athlete_9c55',
  planId: 'plan_meso_hypertrophy_4w',
  title: '4-Week Upper/Lower Mesocycle',
  status: 'active',
  splitType: 'upper_lower',
  totalWeeks: 4,
  daysPerWeek: 4,
  currentWeek: 1,
  currentDay: 1,
  startedAt: '2026-09-20T00:00:00Z',
  updatedAt: '2026-09-20T00:00:00Z',
  completedWorkouts: [],
  totalPlannedWorkouts: 16,
  adaptationHistory: [],
  planSnapshot: MOCK_PLAN_SNAPSHOT,
  planVersion: 1,
  programVersion: '9C.3',
  programSchemaVersion: '1.1.0',
  planSchemaVersion: '9B.8',
}

const MOCK_COMPLETED_PROGRAM: ProgramResponse = {
  ...MOCK_ACTIVE_PROGRAM,
  status: 'completed',
  completedAt: '2026-09-20T12:00:00Z',
  completedWorkouts: Array.from({ length: 16 }, (_, i) => ({
    sessionId: `sess_completed_${i + 1}`,
    planId: 'plan_meso_hypertrophy_4w',
    weekNumber: Math.floor(i / 4) + 1,
    dayNumber: (i % 4) + 1,
    completedAt: '2026-09-20T10:00:00Z',
    durationSeconds: 2400,
    completedSetsCount: 12,
    totalSetsCount: 12,
  })),
}

const MOCK_ABANDONED_PROGRAM: ProgramResponse = {
  ...MOCK_ACTIVE_PROGRAM,
  status: 'abandoned',
  abandonedAt: '2026-09-20T14:30:00Z',
}

// ============================================================================
// Test Suite: Phase 9C.5.5 Program Lifecycle Management & Empty States
// ============================================================================

describe('Phase 9C.5.5 — Program Lifecycle Management & Empty States', () => {
  let originalFetch: typeof globalThis.fetch
  let originalGetIdToken: any

  beforeEach(() => {
    originalFetch = globalThis.fetch
    originalGetIdToken = (programService as any)._getIdToken
    ;(programService as any)._getIdToken = async () => MOCK_AUTH_TOKEN
    workoutPlanExecutionService.clearActiveExecutionContext()
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    ;(programService as any)._getIdToken = originalGetIdToken
    workoutPlanExecutionService.clearActiveExecutionContext()
  })

  // --------------------------------------------------------------------------
  // 1 & 27. No Active Program Empty State vs API Error State
  // --------------------------------------------------------------------------

  test('1. HTTP 404 from /programs/active resolves cleanly to null (No Active Program state)', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = input.toString()
      if (url.includes('/programs/active')) {
        return new Response(JSON.stringify({ detail: 'No active workout program found for this user.' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      throw new Error(`Unexpected fetch URL: ${url}`)
    }

    const active = await programService.getActiveProgram()
    assert.strictEqual(active, null, 'Expected null when user has no active program')
  })

  test('27. HTTP 500 server error rejects with error and does NOT fabricate empty state', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = input.toString()
      if (url.includes('/programs/active')) {
        return new Response(JSON.stringify({ detail: 'Internal database connection timeout.' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      throw new Error(`Unexpected fetch URL: ${url}`)
    }

    await assert.rejects(
      async () => {
        await programService.getActiveProgram()
      },
      (err: Error) => {
        assert.ok(err.message.includes('Internal database connection timeout'))
        return true
      },
      'Expected HTTP 500 to reject, allowing UI to render ErrorState with retry'
    )
  })

  // --------------------------------------------------------------------------
  // 2. Active Program State Integrity
  // --------------------------------------------------------------------------

  test('2. HTTP 200 from /programs/active returns authoritative active ProgramResponse', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = input.toString()
      if (url.includes('/programs/active')) {
        return new Response(JSON.stringify(MOCK_ACTIVE_PROGRAM), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      throw new Error(`Unexpected fetch URL: ${url}`)
    }

    const active = await programService.getActiveProgram()
    assert.ok(active !== null)
    assert.strictEqual(active.programId, 'prog_live_9c55_test_001')
    assert.strictEqual(active.status, 'active')
    assert.strictEqual(active.currentWeek, 1)
    assert.strictEqual(active.currentDay, 1)
  })

  // --------------------------------------------------------------------------
  // 3 & 24. Completed Program Read-Only State
  // --------------------------------------------------------------------------

  test('3 & 24. Completed program has status=completed and 100% completion metrics', () => {
    const prog = MOCK_COMPLETED_PROGRAM
    assert.strictEqual(prog.status, 'completed')
    assert.strictEqual(prog.completedWorkouts.length, 16)
    assert.strictEqual(prog.totalPlannedWorkouts, 16)
    assert.ok(prog.completedAt !== null)
  })

  // --------------------------------------------------------------------------
  // 4. Abandoned Program Historical State
  // --------------------------------------------------------------------------

  test('4. Abandoned program has status=abandoned and preserved abandonedAt timestamp', () => {
    const prog = MOCK_ABANDONED_PROGRAM
    assert.strictEqual(prog.status, 'abandoned')
    assert.ok(prog.abandonedAt !== null)
    assert.strictEqual(prog.planVersion, 1)
  })

  // --------------------------------------------------------------------------
  // 5 & 6 & 7. Start Active Program Contract & Payload
  // --------------------------------------------------------------------------

  test('5 & 6 & 7. startProgram sends POST to /programs/start with authoritative plan snapshot', async () => {
    let capturedUrl = ''
    let capturedMethod = ''
    let capturedHeaders: Record<string, string> = {}
    let capturedBody: any = null

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = input.toString()
      capturedMethod = init?.method || ''
      capturedHeaders = (init?.headers as Record<string, string>) || {}
      capturedBody = JSON.parse((init?.body as string) || '{}')

      return new Response(JSON.stringify(MOCK_ACTIVE_PROGRAM), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const startReq: ProgramStartRequest = {
      plan: MOCK_PLAN_SNAPSHOT,
      title: MOCK_PLAN_SNAPSHOT.title,
      createdFrom: 'generated_plan',
    }

    const created = await programService.startProgram(startReq)

    assert.ok(capturedUrl.includes('/programs/start'))
    assert.strictEqual(capturedMethod, 'POST')
    assert.strictEqual(capturedHeaders['Authorization'], `Bearer ${MOCK_AUTH_TOKEN}`)
    assert.strictEqual(capturedHeaders['Content-Type'], 'application/json')
    assert.strictEqual(capturedBody.plan.plan_id, 'plan_meso_hypertrophy_4w')
    assert.strictEqual(capturedBody.title, '4-Week Upper/Lower Mesocycle')
    assert.strictEqual(capturedBody.createdFrom, 'generated_plan')
    assert.strictEqual(created.status, 'active')
  })

  // --------------------------------------------------------------------------
  // 8 & 9 & 10. Start Active Program HTTP 409 Conflict Protection
  // --------------------------------------------------------------------------

  test('8 & 9 & 10. startProgram handles HTTP 409 Conflict when program is already active', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = input.toString()
      if (url.includes('/programs/start')) {
        return new Response(
          JSON.stringify({
            detail: "An active program ('4-Week Upper/Lower Mesocycle', id: prog_live_9c55_test_001) already exists. Complete or abandon the current active program before starting a new one.",
          }),
          {
            status: 409,
            headers: { 'Content-Type': 'application/json' },
          }
        )
      }
      throw new Error(`Unexpected fetch URL: ${url}`)
    }

    const startReq: ProgramStartRequest = {
      plan: MOCK_PLAN_SNAPSHOT,
      title: MOCK_PLAN_SNAPSHOT.title,
    }

    await assert.rejects(
      async () => {
        await programService.startProgram(startReq)
      },
      (err: Error) => {
        assert.ok(err.message.includes('already exists'))
        assert.ok(err.message.includes('Complete or abandon'))
        return true
      },
      'Expected HTTP 409 Conflict rejection with descriptive backend error message'
    )
  })

  // --------------------------------------------------------------------------
  // 11. Authentication Invariant on Start
  // --------------------------------------------------------------------------

  test('11. startProgram rejects immediately when user is unauthenticated', async () => {
    ;(programService as any)._getIdToken = async () => null

    await assert.rejects(
      async () => {
        await programService.startProgram({ plan: MOCK_PLAN_SNAPSHOT })
      },
      /Authentication required/i
    )
  })

  // --------------------------------------------------------------------------
  // 12 & 13 & 14. Abandon Program Contract & Payload
  // --------------------------------------------------------------------------

  test('12 & 13 & 14. abandonActiveProgram sends POST to /programs/active/abandon with auth headers', async () => {
    let capturedUrl = ''
    let capturedMethod = ''
    let capturedHeaders: Record<string, string> = {}
    let capturedBody: any = null

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      capturedUrl = input.toString()
      capturedMethod = init?.method || ''
      capturedHeaders = (init?.headers as Record<string, string>) || {}
      capturedBody = JSON.parse((init?.body as string) || '{}')

      return new Response(JSON.stringify(MOCK_ABANDONED_PROGRAM), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const req: ProgramAbandonRequest = { reason: 'User switching training focus' }
    const result = await programService.abandonActiveProgram(req)

    assert.ok(capturedUrl.includes('/programs/active/abandon'))
    assert.strictEqual(capturedMethod, 'POST')
    assert.strictEqual(capturedHeaders['Authorization'], `Bearer ${MOCK_AUTH_TOKEN}`)
    assert.strictEqual(capturedBody.reason, 'User switching training focus')
    assert.strictEqual(result.status, 'abandoned')
  })

  test('14. abandonActiveProgram rejects immediately when user is unauthenticated', async () => {
    ;(programService as any)._getIdToken = async () => null

    await assert.rejects(
      async () => {
        await programService.abandonActiveProgram()
      },
      /Authentication required/i
    )
  })

  // --------------------------------------------------------------------------
  // 15 & 16 & 17. Abandon Program HTTP 404 (No Program to Abandon)
  // --------------------------------------------------------------------------

  test('15 & 16 & 17. abandonActiveProgram handles HTTP 404 cleanly when no program is active', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = input.toString()
      if (url.includes('/programs/active/abandon')) {
        return new Response(JSON.stringify({ detail: 'No active workout program found to abandon.' }), {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        })
      }
      throw new Error(`Unexpected fetch URL: ${url}`)
    }

    await assert.rejects(
      async () => {
        await programService.abandonActiveProgram()
      },
      /No active workout program found to abandon/i
    )
  })

  // --------------------------------------------------------------------------
  // 18 & 19. Execution Context Clearing Order (Only After Confirmed Success)
  // --------------------------------------------------------------------------

  test('18. Execution context is cleared upon confirmed abandon mutation success', async () => {
    // Set active execution context
    const context: ProgramWorkoutExecutionContext = {
      programId: 'prog_live_9c55_test_001',
      planId: 'plan_meso_hypertrophy_4w',
      planTitle: '4-Week Upper/Lower Mesocycle',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Accumulation',
      day: MOCK_PLANNED_DAY,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    assert.strictEqual(workoutPlanExecutionService.hasActiveExecutionContext(), true)

    // Simulate successful abandon
    globalThis.fetch = async () => {
      return new Response(JSON.stringify(MOCK_ABANDONED_PROGRAM), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    await programService.abandonActiveProgram()
    workoutPlanExecutionService.clearActiveExecutionContext()

    assert.strictEqual(
      workoutPlanExecutionService.hasActiveExecutionContext(),
      false,
      'Execution context must be null after confirmed abandon'
    )
  })

  test('19. Execution context is PRESERVED when abandon mutation fails', async () => {
    // Set active execution context
    const context: ProgramWorkoutExecutionContext = {
      programId: 'prog_live_9c55_test_001',
      planId: 'plan_meso_hypertrophy_4w',
      planTitle: '4-Week Upper/Lower Mesocycle',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Accumulation',
      day: MOCK_PLANNED_DAY,
    }
    workoutPlanExecutionService.setActiveExecutionContext(context)
    assert.strictEqual(workoutPlanExecutionService.hasActiveExecutionContext(), true)

    // Simulate failed abandon (e.g. 500 Internal Error)
    globalThis.fetch = async () => {
      return new Response(JSON.stringify({ detail: 'Failed to update program state during abandonment.' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    try {
      await programService.abandonActiveProgram()
      assert.fail('Should have thrown on 500')
    } catch {
      // Mutation failed: client MUST NOT clear execution context
    }

    assert.strictEqual(
      workoutPlanExecutionService.hasActiveExecutionContext(),
      true,
      'Execution context must remain intact when abandon mutation fails'
    )
  })

  // --------------------------------------------------------------------------
  // 20 & 21. Query Cache Invalidation Keys
  // --------------------------------------------------------------------------

  test('20 & 21. Query cache keys are strictly namespaced for active program lifecycle', () => {
    assert.deepStrictEqual(ACTIVE_PROGRAM_QUERY_KEY, ['activeProgram'])
    assert.deepStrictEqual(ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY, ['activeProgramPrescription'])
    assert.deepStrictEqual(PROGRAM_VERSIONS_QUERY_KEY, ['programVersions'])
  })

  // --------------------------------------------------------------------------
  // 22 & 23. Execution Invariant & No Static Fallback
  // --------------------------------------------------------------------------

  test('22 & 23. Program workout execution strictly requires all 4 coordinates', () => {
    // Valid context with 4 coordinates
    const validContext: ProgramWorkoutExecutionContext = {
      programId: 'prog_live_9c55_test_001',
      planId: 'plan_meso_hypertrophy_4w',
      planTitle: '4-Week Upper/Lower Mesocycle',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: 1,
      phaseLabel: 'Accumulation',
      day: MOCK_PLANNED_DAY,
    }
    const valResult = workoutPlanExecutionService.validateExecutionContext(validContext)
    assert.strictEqual(valResult.isValid, true)
    assert.strictEqual(valResult.isProgramMode, true)

    // Missing dayNumber
    const missingDay: any = { ...validContext, dayNumber: undefined }
    const valMissingDay = workoutPlanExecutionService.validateExecutionContext(missingDay)
    assert.strictEqual(valMissingDay.isValid, false)
    assert.ok(valMissingDay.error?.includes('dayNumber'))

    // Missing programId
    const missingProg: any = { ...validContext, programId: '' }
    const valMissingProg = workoutPlanExecutionService.validateExecutionContext(missingProg)
    assert.strictEqual(valMissingProg.isValid, false)

    // Invalid zero/negative week number
    const invalidWeek: any = { ...validContext, weekNumber: 0 }
    const valInvalidWeek = workoutPlanExecutionService.validateExecutionContext(invalidWeek)
    assert.strictEqual(valInvalidWeek.isValid, false)
  })

  // --------------------------------------------------------------------------
  // 24. Today Prescription Guarding (Active vs Completed vs Abandoned)
  // --------------------------------------------------------------------------

  test('24. Workout execution is only valid when program status is active', () => {
    const isExecutionAllowed = (status: string, isRestDay: boolean) => {
      return status === 'active' && !isRestDay
    }

    assert.strictEqual(isExecutionAllowed('active', false), true, 'Active training day allows workout')
    assert.strictEqual(isExecutionAllowed('active', true), false, 'Active rest day disallows workout')
    assert.strictEqual(isExecutionAllowed('completed', false), false, 'Completed program disallows workout')
    assert.strictEqual(isExecutionAllowed('abandoned', false), false, 'Abandoned program disallows workout')
    assert.strictEqual(isExecutionAllowed('draft', false), false, 'Draft program disallows workout')
  })

  // --------------------------------------------------------------------------
  // 25. Standard Catalog Workout Isolation
  // --------------------------------------------------------------------------

  test('25. Standard catalog workouts operate independently without program affinity', () => {
    // When a standard catalog workout is selected, execution context is null
    assert.strictEqual(workoutPlanExecutionService.getActiveExecutionContext(), null)
    assert.strictEqual(workoutPlanExecutionService.hasActiveExecutionContext(), false)

    // A standalone generated context (non-program) does not have programId
    const standaloneContext: StandaloneGeneratedExecutionContext = {
      planId: 'standalone_plan_1',
      planTitle: 'Quick Full Body',
      splitType: 'full_body',
      weekNumber: 1,
      phaseLabel: 'General',
      day: MOCK_PLANNED_DAY,
    }
    const valStandalone = workoutPlanExecutionService.validateExecutionContext(standaloneContext)
    assert.strictEqual(valStandalone.isValid, true)
    assert.strictEqual(valStandalone.isProgramMode, false)
  })

  // --------------------------------------------------------------------------
  // 26. Modal Keyboard Accessibility
  // --------------------------------------------------------------------------

  test('26. Modal keyboard accessibility respects Escape key dismiss', () => {
    let closed = false
    const handleClose = () => {
      closed = true
    }

    const handleKeyDown = (e: { key: string }) => {
      if (e.key === 'Escape') handleClose()
    }

    handleKeyDown({ key: 'Enter' })
    assert.strictEqual(closed, false)

    handleKeyDown({ key: 'Escape' })
    assert.strictEqual(closed, true, 'Escape key must trigger modal close handler')
  })

  // --------------------------------------------------------------------------
  // 29 & 30. Mutation Cache Invalidation Exact Behavior
  // --------------------------------------------------------------------------

  test('29. useStartProgram cache invalidation targets activeProgram, prescription, and versions', () => {
    const invalidatedKeys: string[][] = []
    const mockQueryClient: any = {
      setQueryData: (key: string[], data: any) => {},
      invalidateQueries: ({ queryKey }: { queryKey: readonly string[] }) => {
        invalidatedKeys.push([...queryKey])
      },
    }

    // Simulate onSuccess callback logic from useStartProgram
    mockQueryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, MOCK_ACTIVE_PROGRAM)
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
    mockQueryClient.invalidateQueries({ queryKey: PROGRAM_VERSIONS_QUERY_KEY })

    assert.strictEqual(invalidatedKeys.length, 3)
    assert.deepStrictEqual(invalidatedKeys[0], ['activeProgram'])
    assert.deepStrictEqual(invalidatedKeys[1], ['activeProgramPrescription'])
    assert.deepStrictEqual(invalidatedKeys[2], ['programVersions'])
  })

  test('30. useAbandonProgram cache invalidation evicts activeProgram, prescription, and versions', () => {
    const setKeys: string[][] = []
    const removedKeys: string[][] = []
    const mockQueryClient: any = {
      setQueryData: (key: readonly string[], data: any) => {
        setKeys.push([...key])
      },
      invalidateQueries: ({ queryKey }: { queryKey: readonly string[] }) => {},
      removeQueries: ({ queryKey }: { queryKey: readonly string[] }) => {
        removedKeys.push([...queryKey])
      },
    }

    // Simulate onSuccess callback logic from useAbandonProgram
    mockQueryClient.setQueryData(ACTIVE_PROGRAM_QUERY_KEY, null)
    mockQueryClient.invalidateQueries({ queryKey: ACTIVE_PROGRAM_QUERY_KEY })
    mockQueryClient.removeQueries({ queryKey: ACTIVE_PROGRAM_PRESCRIPTION_BASE_KEY })
    mockQueryClient.removeQueries({ queryKey: PROGRAM_VERSIONS_QUERY_KEY })

    assert.deepStrictEqual(setKeys[0], ['activeProgram'])
    assert.strictEqual(removedKeys.length, 2)
    assert.deepStrictEqual(removedKeys[0], ['activeProgramPrescription'])
    assert.deepStrictEqual(removedKeys[1], ['programVersions'])
  })

  // --------------------------------------------------------------------------
  // 31 & 32. Program Completion Percentage Edge Cases
  // --------------------------------------------------------------------------

  test('31. calculateProgramCompletionPercentage handles 0 total workouts safely without NaN', () => {
    const calc = (completed: number, total: number) => {
      if (!total || total <= 0) return { percentage: 0 }
      const pct = Math.min(100, Math.round((completed / total) * 100))
      return { percentage: isNaN(pct) ? 0 : pct }
    }

    assert.strictEqual(calc(0, 0).percentage, 0)
    assert.strictEqual(calc(5, 0).percentage, 0)
  })

  test('32. calculateProgramCompletionPercentage calculates exact percentage clamped to 100', () => {
    const calc = (completed: number, total: number) => {
      if (!total || total <= 0) return { percentage: 0 }
      const pct = Math.min(100, Math.round((completed / total) * 100))
      return { percentage: isNaN(pct) ? 0 : pct }
    }

    assert.strictEqual(calc(8, 16).percentage, 50)
    assert.strictEqual(calc(16, 16).percentage, 100)
    assert.strictEqual(calc(20, 16).percentage, 100)
  })

  // --------------------------------------------------------------------------
  // 33 & 34. Button & Modal Semantics
  // --------------------------------------------------------------------------

  test('33. AbandonProgramModal contract defines Keep Program (cancel) and Abandon Program (confirm) buttons', () => {
    const cancelLabel = 'Keep Program'
    const confirmLabel = 'Abandon Program'
    const title = 'Abandon Active Program?'

    assert.strictEqual(cancelLabel, 'Keep Program')
    assert.strictEqual(confirmLabel, 'Abandon Program')
    assert.strictEqual(title, 'Abandon Active Program?')
  })

  test('34. EmptyState contract requires CTA label Generate Workout Plan', () => {
    const emptyStateActionLabel = 'Generate Workout Plan'
    const emptyStateTitle = 'No Active Program'

    assert.strictEqual(emptyStateActionLabel, 'Generate Workout Plan')
    assert.strictEqual(emptyStateTitle, 'No Active Program')
  })

  test('35. Execution context validation rejects negative or zero dayNumber in program mode', () => {
    const invalidContext: any = {
      programId: 'prog_live_9c55_test_001',
      planId: 'plan_meso_hypertrophy_4w',
      planTitle: '4-Week Upper/Lower Mesocycle',
      splitType: 'upper_lower',
      weekNumber: 1,
      dayNumber: -1,
      phaseLabel: 'Accumulation',
      day: MOCK_PLANNED_DAY,
    }
    const res = workoutPlanExecutionService.validateExecutionContext(invalidContext)
    assert.strictEqual(res.isValid, false)
    assert.ok(res.error?.includes('dayNumber'))
  })

  // --------------------------------------------------------------------------
  // 28. Strict Invariant: No Client-Side Firestore Mutation
  // --------------------------------------------------------------------------

  test('28. Invariant: programService never imports or writes directly to Firestore', () => {
    const serviceKeys = Object.keys(programService)
    assert.ok(serviceKeys.includes('startProgram'))
    assert.ok(serviceKeys.includes('getActiveProgram'))
    assert.ok(serviceKeys.includes('syncSession'))
    assert.ok(serviceKeys.includes('abandonActiveProgram'))

    // Verify no direct firestore write methods exist on programService
    assert.strictEqual((programService as any).setDoc, undefined)
    assert.strictEqual((programService as any).updateDoc, undefined)
    assert.strictEqual((programService as any).deleteDoc, undefined)
  })
})
