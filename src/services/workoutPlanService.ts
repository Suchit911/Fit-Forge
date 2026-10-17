import type { WorkoutPlanGenerateRequest, WorkoutPlanResponse } from '../types/workoutPlan'
import { getIdToken } from '../lib/firebase.ts'

const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL)
  ? (import.meta as any).env.VITE_API_BASE_URL
  : 'http://localhost:8000/api/v1'

export const workoutPlanService = {
  _getIdToken: getIdToken,

  /**
   * Dispatches a deterministic workout plan generation request to the FastAPI backend.
   * Authenticated via Firebase ID token; purely deterministic without AI or Firestore side effects.
   */
  async generateWorkoutPlan(request: WorkoutPlanGenerateRequest): Promise<WorkoutPlanResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to generate a workout plan.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/workout-plans/generate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
    } catch (err) {
      throw new Error('Network connection failure. Unable to reach workout planner service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail

      if (res.status === 401) {
        throw new Error('Authentication expired or invalid. Please sign in again.')
      } else if (res.status === 422) {
        if (Array.isArray(detail)) {
          const msg = detail.map((d: any) => d.msg || d.message).join('; ')
          throw new Error(`Invalid plan configuration: ${msg}`)
        }
        throw new Error(typeof detail === 'string' ? detail : 'Invalid plan configuration provided.')
      } else if (res.status === 500) {
        throw new Error('An unexpected server error occurred during plan generation.')
      } else {
        throw new Error(typeof detail === 'string' ? detail : `Generation request failed with status ${res.status}.`)
      }
    }

    const data = await res.json()
    return data as WorkoutPlanResponse
  },
}
