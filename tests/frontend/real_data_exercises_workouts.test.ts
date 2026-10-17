/**
 * Real-Data Remediation — Stage 3 Test Suite:
 * Verify Removal of Frontend Exercise and Workout Mocks.
 *
 * Proves:
 * 1. API exercise results are returned directly without falling back to mockExercises.
 * 2. A legitimate empty exercise response returns [] (enables UI empty state).
 * 3. Exercise API failure propagates ExerciseApiError and never conceals with mock records.
 * 4. Unknown exercise ID never resolves to Bench Press or another fallback exercise.
 * 5. Exercise HTTP 404 resolves cleanly to null (explicit not-found state).
 * 6. Successful empty workout history returns [] and does not fabricate past workouts.
 * 7. Workout API failure throws structured error and never falls back to mockWorkouts.
 * 8. Today workout returns null on HTTP 404 and does not default to mockWorkouts[0].
 * 9. Failed workout writes reject and never fabricate success objects or mock session IDs.
 * 10. Successful writes return success only upon verified backend confirmation.
 * 11. Query retry flow recovers cleanly from transient error to fresh real data.
 * 12. Authenticated headers, query filter serialization, and payload contracts are preserved.
 */

import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

import { exerciseService, ExerciseApiError } from '../../src/services/exerciseService.ts'
import { workoutService } from '../../src/services/workoutService.ts'
import type { Exercise, Workout, WorkoutSessionData } from '../../src/types/index.ts'

// ============================================================================
// TEST FIXTURES & HELPERS
// ============================================================================

const canonicalExerciseFixture: Exercise = {
  id: 'canonical_pushup',
  name: 'Standard Push-Up',
  description: 'Authoritative pushup from canonical catalog',
  primaryMuscles: ['chest'],
  secondaryMuscles: ['triceps', 'shoulders'],
  equipment: ['bodyweight'],
  difficulty: 'beginner',
  category: 'strength',
  instructions: ['Start in high plank', 'Lower body until chest grazes floor', 'Push back up'],
  commonMistakes: ['Sagging hips'],
  safetyNotes: ['Keep core braced'],
  supportedFormAnalysis: true,
}

const canonicalWorkoutFixture: Workout = {
  id: 'wkt_canonical_full_body',
  title: 'Canonical Full Body Routine',
  description: 'Verified real routine from backend catalog',
  targetEnvironment: 'gym',
  difficulty: 'intermediate',
  estimatedDurationMinutes: 50,
  exercises: [
    {
      exerciseId: 'canonical_pushup',
      exercise: canonicalExerciseFixture,
      order: 1,
      restSecondsBetweenSets: 90,
      sets: [
        { setNumber: 1, targetReps: 12 },
        { setNumber: 2, targetReps: 12 },
      ],
    },
  ],
}

let originalFetch: typeof globalThis.fetch
let originalGetIdToken: typeof workoutService._getIdToken

describe('Stage 3: Remove Frontend Exercise and Workout Mocks', () => {
  beforeEach(() => {
    originalFetch = globalThis.fetch
    originalGetIdToken = workoutService._getIdToken
    workoutService._getIdToken = async () => 'test-valid-firebase-jwt-token'
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    workoutService._getIdToken = originalGetIdToken
  })

  // ==========================================================================
  // EXERCISE SERVICE TESTS
  // ==========================================================================

  test('1. API exercise results are returned without falling back to mockExercises', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = String(input)
      assert.ok(url.includes('/exercises'), `Expected exercises URL, got ${url}`)
      return new Response(JSON.stringify([canonicalExerciseFixture]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const exercises = await exerciseService.getExercises()
    assert.equal(exercises.length, 1)
    assert.equal(exercises[0].id, 'canonical_pushup')
    assert.equal(exercises[0].name, 'Standard Push-Up')
    // Must NOT contain mock exercises like 'ex_bench_press' or 'ex_squat'
    assert.ok(!exercises.some((e) => e.id === 'ex_bench_press'))
    assert.ok(!exercises.some((e) => e.id === 'ex_squat'))
  })

  test('2. A successful empty exercise response returns legitimate empty []', async () => {
    globalThis.fetch = async () => {
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const exercises = await exerciseService.getExercises({ muscle: 'chest' })
    assert.equal(Array.isArray(exercises), true)
    assert.equal(exercises.length, 0, 'Must return empty array, NOT fallback to mockExercises')
  })

  test('3. Exercise API failure throws ExerciseApiError and never conceals with mock records', async () => {
    globalThis.fetch = async () => {
      return new Response(JSON.stringify({ detail: 'Internal Server Error' }), {
        status: 500,
        statusText: 'Internal Server Error',
        headers: { 'Content-Type': 'application/json' },
      })
    }

    await assert.rejects(
      async () => {
        await exerciseService.getExercises()
      },
      (err: any) => {
        assert.ok(err instanceof ExerciseApiError, 'Error must be an instance of ExerciseApiError')
        assert.equal(err.status, 500)
        return true
      }
    )
  })

  test('4. Exercise network failure throws ExerciseApiError and does not return mock records', async () => {
    globalThis.fetch = async () => {
      throw new Error('Connection reset by peer')
    }

    await assert.rejects(
      async () => {
        await exerciseService.getExercises()
      },
      (err: any) => {
        assert.ok(err instanceof ExerciseApiError)
        assert.ok(err.message.includes('Connection reset by peer'))
        return true
      }
    )
  })

  test('5. Unknown exercise ID never resolves to Bench Press or another unrelated exercise', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('nonexistent_exercise_999')) {
        return new Response(JSON.stringify({ detail: 'Exercise not found' }), {
          status: 404,
          statusText: 'Not Found',
          headers: { 'Content-Type': 'application/json' },
        })
      }
      return new Response('{}', { status: 500 })
    }

    const result = await exerciseService.getExerciseById('nonexistent_exercise_999')
    assert.equal(result, null, 'Unknown exercise must return null, NEVER Bench Press or mock fallback')

    const emptyIdResult = await exerciseService.getExerciseById('')
    assert.equal(emptyIdResult, null, 'Empty ID must resolve to null')
  })

  test('6. Exercise HTTP 404 explicitly returns null for detail page not-found state', async () => {
    globalThis.fetch = async () => {
      return new Response(JSON.stringify({ detail: 'Exercise with ID ex_deleted was not found' }), {
        status: 404,
        statusText: 'Not Found',
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const result = await exerciseService.getExerciseById('ex_deleted')
    assert.equal(result, null)
  })

  test('7. Exercise detail API 500 throws ExerciseApiError with status code', async () => {
    globalThis.fetch = async () => {
      return new Response(JSON.stringify({ detail: 'Database error' }), {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' },
      })
    }

    await assert.rejects(
      async () => {
        await exerciseService.getExerciseById('ex_any')
      },
      (err: any) => {
        assert.ok(err instanceof ExerciseApiError)
        assert.equal(err.status, 503)
        return true
      }
    )
  })

  // ==========================================================================
  // WORKOUT SERVICE TESTS
  // ==========================================================================

  test('8. Successful empty workout history does not display mock workouts', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = String(input)
      assert.ok(url.includes('/workouts/history'))
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const history = await workoutService.getWorkoutHistory()
    assert.equal(Array.isArray(history), true)
    assert.equal(history.length, 0, 'New user must see empty history, NOT fabricated past sessions')
  })

  test('9. Workout catalog API failure throws Error and does not display mock history', async () => {
    globalThis.fetch = async () => {
      return new Response('Database timeout', {
        status: 504,
        statusText: 'Gateway Timeout',
      })
    }

    await assert.rejects(
      async () => {
        await workoutService.getWorkouts()
      },
      (err: any) => {
        assert.ok(err.message.includes('504'))
        return true
      }
    )
  })

  test('10. Workout history API failure throws Error and does not swallow failure', async () => {
    globalThis.fetch = async () => {
      return new Response('Unauthorized token', {
        status: 401,
        statusText: 'Unauthorized',
      })
    }

    await assert.rejects(
      async () => {
        await workoutService.getWorkoutHistory()
      },
      (err: any) => {
        assert.ok(err.message.includes('401'))
        return true
      }
    )
  })

  test('11. Today workout returns null on HTTP 404 and does not default to mockWorkouts[0]', async () => {
    globalThis.fetch = async (input: RequestInfo | URL) => {
      const url = String(input)
      assert.ok(url.includes('/workouts/today'))
      return new Response(JSON.stringify({ detail: 'No workout scheduled today' }), {
        status: 404,
        statusText: 'Not Found',
      })
    }

    const today = await workoutService.getTodayWorkout()
    assert.equal(today, null, 'Missing today workout must return null, NEVER Upper Body Push mock')
  })

  test('12. Today workout returns real routine when present', async () => {
    globalThis.fetch = async () => {
      return new Response(JSON.stringify(canonicalWorkoutFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    const today = await workoutService.getTodayWorkout()
    assert.ok(today)
    assert.equal(today?.id, 'wkt_canonical_full_body')
    assert.equal(today?.title, 'Canonical Full Body Routine')
  })

  test('13. Failed workout write rejects and never reports fake success', async () => {
    // Session creation succeeds, but completion fails
    let callIndex = 0
    globalThis.fetch = async (input: RequestInfo | URL) => {
      callIndex++
      const url = String(input)
      if (url.includes('/sessions') && !url.includes('/complete')) {
        return new Response(
          JSON.stringify({
            id: 'sess_real_777',
            status: 'in_progress',
            startedAt: new Date().toISOString(),
          }),
          { status: 201, headers: { 'Content-Type': 'application/json' } }
        )
      }
      if (url.includes('/complete')) {
        return new Response('Database write error', {
          status: 500,
          statusText: 'Internal Server Error',
        })
      }
      return new Response('{}', { status: 500 })
    }

    await assert.rejects(
      async () => {
        await workoutService.logWorkoutSession('wkt_canonical_full_body', 1800, 8)
      },
      (err: any) => {
        assert.ok(err.message.includes('Failed to complete workout session'))
        return true
      }
    )
  })

  test('14. Unauthenticated workout write rejects immediately', async () => {
    workoutService._getIdToken = async () => null

    await assert.rejects(
      async () => {
        await workoutService.logWorkoutSession('wkt_test', 1200, 5)
      },
      (err: any) => {
        assert.ok(err.message.includes('Authentication required'))
        return true
      }
    )
  })

  test('15. Successful write displays success only after confirmed API completion', async () => {
    const recordedCalls: { url: string; authHeader: string; body: any }[] = []

    globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const authHeader = (init?.headers as Record<string, string>)?.['Authorization'] || ''
      const body = init?.body ? JSON.parse(String(init.body)) : null
      recordedCalls.push({ url, authHeader, body })

      if (url.includes('/sessions') && !url.includes('/complete')) {
        return new Response(
          JSON.stringify({
            id: 'sess_authoritative_99',
            status: 'in_progress',
            startedAt: '2026-10-16T12:00:00.000Z',
          }),
          { status: 201, headers: { 'Content-Type': 'application/json' } }
        )
      }
      if (url.includes('/complete')) {
        return new Response(
          JSON.stringify({
            id: 'sess_authoritative_99',
            status: 'completed',
            completedAt: '2026-10-16T12:30:00.000Z',
            durationSeconds: 1800,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      }
      return new Response('{}', { status: 404 })
    }

    const result = await workoutService.logWorkoutSession('wkt_canonical_full_body', 1800, 10)
    assert.equal(result.success, true)
    assert.ok(result.loggedAt)

    assert.equal(recordedCalls.length, 2)
    assert.ok(recordedCalls[0].url.includes('/workouts/wkt_canonical_full_body/sessions'))
    assert.equal(recordedCalls[0].authHeader, 'Bearer test-valid-firebase-jwt-token')
    assert.ok(recordedCalls[1].url.includes('/sessions/sess_authoritative_99/complete'))
    assert.equal(recordedCalls[1].authHeader, 'Bearer test-valid-firebase-jwt-token')
    assert.equal(recordedCalls[1].body.durationSeconds, 1800)
  })

  // ==========================================================================
  // RETRY & RECOVERY SEMANTICS
  // ==========================================================================

  test('16. Retry controls repeat request and recover when API becomes available', async () => {
    let attempt = 0
    globalThis.fetch = async () => {
      attempt++
      if (attempt === 1) {
        return new Response('Internal Server Error', { status: 500, statusText: 'Server Error' })
      }
      return new Response(JSON.stringify([canonicalExerciseFixture]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    // First attempt fails with ExerciseApiError
    await assert.rejects(
      async () => {
        await exerciseService.getExercises()
      },
      ExerciseApiError
    )

    // Retry succeeds with actual data
    const retryExercises = await exerciseService.getExercises()
    assert.equal(retryExercises.length, 1)
    assert.equal(retryExercises[0].id, 'canonical_pushup')
    assert.equal(attempt, 2, 'Must have performed 2 fetches total')
  })

  // ==========================================================================
  // FILTER SERIALIZATION & AUTH INTEGRITY
  // ==========================================================================

  test('17. Exercise filters are properly encoded into URL query parameters', async () => {
    let capturedUrl = ''
    globalThis.fetch = async (input: RequestInfo | URL) => {
      capturedUrl = String(input)
      return new Response(JSON.stringify([]), { status: 200, headers: { 'Content-Type': 'application/json' } })
    }

    await exerciseService.getExercises({
      muscle: 'chest',
      equipment: 'resistance bands',
      difficulty: 'intermediate',
      category: 'strength',
      searchQuery: 'bench',
    })

    assert.ok(capturedUrl.includes('muscle=chest'), 'Muscle param encoded')
    assert.ok(capturedUrl.includes('equipment=resistance_bands'), 'Equipment space-to-underscore converted')
    assert.ok(capturedUrl.includes('difficulty=intermediate'), 'Difficulty param encoded')
    assert.ok(capturedUrl.includes('category=strength'), 'Category param encoded')
    assert.ok(capturedUrl.includes('search=bench'), 'Search param encoded')
  })
})
