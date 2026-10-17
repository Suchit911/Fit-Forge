import type { FormAnalysisSession } from '../types'
import type { FormAnalysisSessionSummary, FormAnalysisSessionDetail } from '../types/formStream'
import { getIdToken } from '../lib/firebase.ts'
import {
  resolveCVExerciseId,
  VERIFIED_CV_EXERCISES,
} from '../utils/formAnalysisCapability.ts'

const API_BASE_URL =
  (typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : null) ||
  'http://localhost:8000/api/v1'

/**
 * Returns a genuine zero-state baseline for an exercise before any repetitions or
 * telemetry have been recorded. Contains zero fabricated repetitions, scores, or issues.
 */
export function getInitialSessionBaseline(exerciseId: string): FormAnalysisSession {
  const resolved = resolveCVExerciseId(exerciseId)
  const meta = resolved ? VERIFIED_CV_EXERCISES[resolved] : null
  const exerciseName = meta?.name || 'Form Analysis'

  return {
    exerciseId: meta?.canonicalId || exerciseId,
    exerciseName,
    setInfo: 'Ready to Record',
    weightKg: 0,
    reps: 0,
    rpe: 0,
    restTime: '01:30 Rest',
    formScore: 0,
    formStatus: 'Ready',
    analysisTime: '00:00',
    confidence: 'Awaiting Stream',
    videoAssetUrl: '/assets/dashboard_push_lifter.jpg',
    keyMetrics: [],
    scoreBreakdown: [],
    muscleActivation: [],
    positiveFeedback: [],
    improvementFeedback: [],
    infoFeedback: [],
    coachingTips: [
      'Ensure your entire body and joints remain visible in the camera viewport.',
      'Perform repetitions with controlled tempo and full range of motion.',
      'Heuristic metrics and rep counts update authoritatively from the live vision stream.',
    ],
    repProgress: [],
    history: [],
  }
}

export const formAnalysisService = {
  /**
   * Retrieves baseline exercise configuration.
   * Connects to authoritative API when authenticated, or returns genuine zero-state baseline.
   * Completely free of fabricated metrics, scores, or repetitions.
   */
  async getFormAnalysisSession(exerciseId: string = 'squat'): Promise<FormAnalysisSession> {
    const token = await getIdToken()
    if (token) {
      try {
        const res = await fetch(`${API_BASE_URL}/form-analysis/session/${encodeURIComponent(exerciseId)}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
        if (res.ok) {
          return (await res.json()) as FormAnalysisSession
        }
      } catch {
        // Fall back to clean zero-state baseline on network disconnect
      }
    }

    return getInitialSessionBaseline(exerciseId)
  },

  // ==========================================================================
  // PHASE 9B.7: AUTHENTICATED REAL API METHODS
  // ==========================================================================

  /**
   * Retrieves completed form analysis session summaries for the verified user.
   */
  async getHistory(limit: number = 20, exerciseId?: string): Promise<FormAnalysisSessionSummary[]> {
    const token = await getIdToken()
    const params = new URLSearchParams()
    if (limit) params.set('limit', String(Math.min(Math.max(1, limit), 50)))
    if (exerciseId && exerciseId.trim()) params.set('exercise_id', exerciseId.trim())

    const res = await fetch(`${API_BASE_URL}/form-analysis/history?${params.toString()}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        throw new Error('Authentication required to access form analysis history.')
      }
      throw new Error(`Failed to fetch form analysis history (Status ${res.status}).`)
    }

    const data = await res.json()
    return Array.isArray(data) ? data : []
  },

  /**
   * Retrieves detailed metrics, category breakdown, and rep summaries for a finalized session.
   */
  async getSessionDetail(sessionId: string): Promise<FormAnalysisSessionDetail> {
    const token = await getIdToken()
    const res = await fetch(`${API_BASE_URL}/form-analysis/history/${encodeURIComponent(sessionId)}`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    })

    if (!res.ok) {
      if (res.status === 404) {
        throw new Error('Form analysis session not found.')
      }
      throw new Error(`Failed to load session details (Status ${res.status}).`)
    }

    return await res.json()
  },

  /**
   * Authoritatively finalizes an active in-memory session via REST.
   */
  async finalizeSession(sessionId: string, clientDurationSeconds?: number): Promise<FormAnalysisSessionDetail> {
    const token = await getIdToken()
    const payload = clientDurationSeconds ? { client_duration_seconds: clientDurationSeconds } : {}

    const res = await fetch(`${API_BASE_URL}/form-analysis/sessions/${encodeURIComponent(sessionId)}/finalize`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Failed to finalize session (Status ${res.status}).`)
    }

    return await res.json()
  },
}
