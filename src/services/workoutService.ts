import type { Workout, WorkoutSet } from '../types'
import { getIdToken } from '../lib/firebase.ts'

const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL)
  ? (import.meta as any).env.VITE_API_BASE_URL
  : 'http://localhost:8000/api/v1'

export interface WorkoutSessionData {
  id: string
  userId: string
  workoutId: string
  workoutTitle: string
  status: 'in_progress' | 'completed' | 'cancelled'
  startedAt: string
  completedAt?: string
  durationSeconds: number
  currentExerciseIndex: number
  currentSetIndex: number
  isPaused: boolean
  completedSets: Record<string, WorkoutSet[]>
  completedSetsCount: number
  totalSetsCount: number
  totalVolumeKg: number
  caloriesBurned: number
  notes?: string
  programId?: string | null
  planId?: string | null
  weekNumber?: number | null
  dayNumber?: number | null
}

export const workoutService = {
  _getIdToken: getIdToken,

  /**
   * Fetches all available workout routines from FastAPI backend.
   * Throws Error on network or server failure. Returns empty array if none found.
   */
  async getWorkouts(): Promise<Workout[]> {
    const res = await fetch(`${API_BASE_URL}/workouts`)
    if (!res.ok) {
      throw new Error(`Failed to fetch workouts (${res.status}): ${res.statusText}`)
    }
    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format: expected workout list')
    }
    return data as Workout[]
  },

  /**
   * Fetches today's featured routine.
   * Returns null if 404. Throws Error on network or server failure.
   */
  async getTodayWorkout(): Promise<Workout | null> {
    const res = await fetch(`${API_BASE_URL}/workouts/today`)
    if (res.status === 404) {
      return null
    }
    if (!res.ok) {
      throw new Error(`Failed to fetch today's workout (${res.status}): ${res.statusText}`)
    }
    return (await res.json()) as Workout
  },

  /**
   * Fetches workout details by ID.
   * Returns null on 404 or missing ID. Throws Error on network or server failure.
   */
  async getWorkoutById(id: string): Promise<Workout | null> {
    if (!id || !id.trim()) {
      return null
    }

    const res = await fetch(`${API_BASE_URL}/workouts/${encodeURIComponent(id)}`)
    if (res.status === 404) {
      return null
    }
    if (!res.ok) {
      throw new Error(`Failed to fetch workout details (${res.status}): ${res.statusText}`)
    }
    return (await res.json()) as Workout
  },

  /**
   * Starts a new workout session for the authenticated user.
   * Supports optional program affinity parameters (Phase 9C.5.1).
   * Throws Error on failure to ensure caller receives failure signal.
   */
  async startWorkoutSession(
    workoutId: string,
    notes?: string,
    workoutTitle?: string,
    totalSetsCount?: number,
    programId?: string,
    planId?: string,
    weekNumber?: number,
    dayNumber?: number
  ): Promise<WorkoutSessionData> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required to start workout session')
    }

    const payload: Record<string, any> = {
      workoutId,
      notes,
      workoutTitle,
      totalSetsCount,
    }
    if (programId) payload.programId = programId
    if (planId) payload.planId = planId
    if (weekNumber !== undefined && weekNumber !== null) payload.weekNumber = weekNumber
    if (dayNumber !== undefined && dayNumber !== null) payload.dayNumber = dayNumber

    const res = await fetch(`${API_BASE_URL}/workouts/${encodeURIComponent(workoutId)}/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const errBody = await res.text().catch(() => '')
      throw new Error(`Failed to start workout session (${res.status}): ${errBody || res.statusText}`)
    }

    return (await res.json()) as WorkoutSessionData
  },

  /**
   * Retrieves the currently active workout session for the user, or null if none.
   */
  async getActiveSession(): Promise<WorkoutSessionData | null> {
    const token = await this._getIdToken()
    if (!token) return null

    const res = await fetch(`${API_BASE_URL}/workouts/sessions/active`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    if (res.status === 404) {
      return null
    }
    if (!res.ok) {
      throw new Error(`Failed to fetch active session (${res.status}): ${res.statusText}`)
    }
    const data = await res.json()
    return data as WorkoutSessionData | null
  },

  /**
   * Updates progress of an active workout session.
   * Throws Error on failure to ensure caller receives failure signal.
   */
  async updateWorkoutSession(
    sessionId: string,
    updates: {
      currentExerciseIndex?: number
      currentSetIndex?: number
      elapsedSeconds?: number
      isPaused?: boolean
      recordedSet?: {
        exerciseId: string
        setNumber: number
        actualReps: number
        actualWeightKg: number
        rpe?: number
      }
      notes?: string
    }
  ): Promise<WorkoutSessionData> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required to update workout session')
    }

    const res = await fetch(`${API_BASE_URL}/workouts/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(updates),
    })

    if (!res.ok) {
      const errBody = await res.text().catch(() => '')
      throw new Error(`Failed to update workout session (${res.status}): ${errBody || res.statusText}`)
    }

    return (await res.json()) as WorkoutSessionData
  },

  /**
   * Completes a workout session and calculates volume and caloric burn.
   * Throws Error on failure.
   */
  async completeWorkoutSession(
    sessionId: string,
    durationSeconds: number,
    notes?: string
  ): Promise<WorkoutSessionData> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required to complete workout session')
    }

    const res = await fetch(`${API_BASE_URL}/workouts/sessions/${encodeURIComponent(sessionId)}/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ durationSeconds, notes }),
    })

    if (!res.ok) {
      const errBody = await res.text().catch(() => '')
      throw new Error(`Failed to complete workout session (${res.status}): ${errBody || res.statusText}`)
    }

    return (await res.json()) as WorkoutSessionData
  },

  /**
   * Retrieves user's past workout history.
   * Propagates errors on API failure; returns empty list on legitimate empty history.
   */
  async getWorkoutHistory(limit = 20): Promise<WorkoutSessionData[]> {
    const token = await this._getIdToken()
    if (!token) return []

    const res = await fetch(`${API_BASE_URL}/workouts/history?limit=${limit}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
    if (!res.ok) {
      throw new Error(`Failed to fetch workout history (${res.status}): ${res.statusText}`)
    }
    const data = await res.json()
    if (!Array.isArray(data)) {
      throw new Error('Invalid response format: expected workout history list')
    }
    return data as WorkoutSessionData[]
  },

  /**
   * Verified session logger.
   * Only returns success after authenticated backend confirmation.
   * Throws Error on failure so the caller/UI can never report fake success.
   */
  async logWorkoutSession(
    workoutId: string,
    durationSeconds: number,
    _completedSetsCount: number
  ): Promise<{ success: boolean; loggedAt: string }> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required to log workout session')
    }

    const session = await this.startWorkoutSession(workoutId)
    if (!session || !session.id) {
      throw new Error('Failed to create workout session')
    }

    await this.completeWorkoutSession(session.id, durationSeconds)
    return {
      success: true,
      loggedAt: new Date().toISOString(),
    }
  },
}

