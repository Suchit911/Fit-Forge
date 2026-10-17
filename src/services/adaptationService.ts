/**
 * Deterministic Progression & Adaptation Engine API Client (Phase 9C.2).
 * Authenticated via Firebase ID token; queries read-only adaptation endpoints.
 */

import type {
  AdaptationEvaluationRequest,
  AdaptationEvaluationResponse,
} from '../types/adaptation'
import { getIdToken } from '../lib/firebase.ts'

const API_BASE_URL =
  typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL
    ? (import.meta as any).env.VITE_API_BASE_URL
    : 'http://localhost:8000/api/v1'

export const adaptationService = {
  _getIdToken: getIdToken,

  /**
   * Fetches evaluated workout adaptations for the authenticated user.
   * Read-only: evaluates current user data without Firestore writes.
   */
  async getAdaptations(windowDays = 28): Promise<AdaptationEvaluationResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to view adaptation decisions.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/personalization/adaptations?window_days=${windowDays}`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach adaptation decision service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to load adaptation decisions.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as AdaptationEvaluationResponse
  },

  /**
   * Evaluates adaptations against a specific candidate workout context.
   * Read-only: does not persist adaptations or mutate active programs.
   */
  async evaluateAdaptations(
    request: AdaptationEvaluationRequest
  ): Promise<AdaptationEvaluationResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to evaluate adaptations.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/personalization/adaptations/evaluate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach adaptation decision service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to evaluate adaptations.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as AdaptationEvaluationResponse
  },
}
