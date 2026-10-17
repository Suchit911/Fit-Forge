/**
 * Program & Mesocycle Lifecycle API Client (Phase 9C.3).
 * Authenticated via Firebase ID token.
 * Provides client methods to start, query, synchronize, and abandon active programs.
 */

import type {
  ProgramResponse,
  ProgramStartRequest,
  ProgramSyncSessionRequest,
  ProgramAbandonRequest,
  EffectivePrescriptionResponse,
  ApplyAdaptationRequest,
  ApplyAdaptationResponse,
  ProgramVersionsResponse,
} from '../types/program'
import { getIdToken } from '../lib/firebase.ts'

const API_BASE_URL =
  typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL
    ? (import.meta as any).env.VITE_API_BASE_URL
    : 'http://localhost:8000/api/v1'

export const programService = {
  _getIdToken: getIdToken,

  /**
   * Starts a new persistent workout program from a generated plan.
   * Rejects with 409 if user already has an active program.
   */
  async startProgram(request: ProgramStartRequest): Promise<ProgramResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to start a program.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/start`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach program service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to start workout program.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ProgramResponse
  },

  /**
   * Retrieves the currently active workout program for the authenticated user.
   * Returns null if no active program exists (HTTP 404).
   */
  async getActiveProgram(): Promise<ProgramResponse | null> {
    const token = await this._getIdToken()
    if (!token) {
      return null
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/active`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach program service.')
    }

    if (res.status === 404) {
      return null
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to fetch active program.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ProgramResponse
  },

  /**
   * Synchronizes a completed workout session with the active program.
   * Idempotent: safe to invoke multiple times for the same session.
   */
  async syncSession(request: ProgramSyncSessionRequest): Promise<ProgramResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to sync session.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/active/sync-session`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach program service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to sync workout session to program.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ProgramResponse
  },

  /**
   * Abandons the active program without deleting historical completed workouts or sessions.
   */
  async abandonActiveProgram(request?: ProgramAbandonRequest): Promise<ProgramResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to abandon program.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/active/abandon`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request || {}),
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach program service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to abandon active program.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ProgramResponse
  },

  /**
   * Retrieves any program by ID for the authenticated user.
   */
  async getProgramById(programId: string): Promise<ProgramResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to fetch program.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/${programId}`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach program service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || `Failed to fetch program ${programId}.`
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ProgramResponse
  },

  /**
   * Retrieves the current effective prescription for a specified week and day (Phase 9C.4).
   */
  async getEffectivePrescription(week: number, day: number): Promise<EffectivePrescriptionResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/active/prescription/${week}/${day}`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach prescription service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || `Failed to fetch effective prescription for Week ${week} Day ${day}.`
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as EffectivePrescriptionResponse
  },

  /**
   * Atomically applies an approved Phase 9C.2 adaptation decision to future workouts (Phase 9C.4).
   */
  async applyAdaptation(request: ApplyAdaptationRequest): Promise<ApplyAdaptationResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/active/apply-adaptation`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach adaptation service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to apply adaptation.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ApplyAdaptationResponse
  },

  /**
   * Retrieves active program versions and adaptation audit history (Phase 9C.4).
   */
  async getProgramVersions(): Promise<ProgramVersionsResponse> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in.')
    }

    let res: Response
    try {
      res = await fetch(`${API_BASE_URL}/programs/active/versions`, {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
    } catch {
      throw new Error('Network connection failure. Unable to reach program versions service.')
    }

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || 'Failed to fetch program versions.'
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
    }

    return (await res.json()) as ProgramVersionsResponse
  },
}
