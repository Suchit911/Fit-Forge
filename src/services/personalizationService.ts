/**
 * Personalization & Adaptive Signals API Client (Phase 9C.1).
 * Authenticated via Firebase ID token; queries read-only analytics endpoints.
 */

import type { PersonalizationSignalsResponse, ExercisePerformanceSummary } from '../types/personalization'
import { getIdToken } from '../lib/firebase.ts'

const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL)
  ? (import.meta as any).env.VITE_API_BASE_URL
  : 'http://localhost:8000/api/v1'

export const personalizationService = {
  _getIdToken: getIdToken,

  /**
   * Fetches the user's personalization signals and performance analytics snapshot.
   */
  async getPersonalizationSignals(windowDays = 28): Promise<PersonalizationSignalsResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to access personalization signals.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/personalization/signals?window_days=${windowDays}`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch (err) {
      throw new Error('Network connection failure. Unable to reach personalization analytics service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to load personalization signals.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as PersonalizationSignalsResponse
  },

  /**
   * Fetches performance signals for a single canonical exercise.
   */
  async getExercisePerformanceSignal(exerciseId: string): Promise<ExercisePerformanceSummary> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to access exercise signals.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/personalization/exercises/${encodeURIComponent(exerciseId)}`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch (err) {
      throw new Error('Network connection failure. Unable to reach personalization analytics service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || `Failed to load performance signals for exercise '${exerciseId}'.`
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ExercisePerformanceSummary
  },
}
