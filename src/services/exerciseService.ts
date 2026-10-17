import type { Exercise, MuscleGroup, EquipmentType, DifficultyLevel } from '../types'

const API_BASE_URL = (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL)
  ? (import.meta as any).env.VITE_API_BASE_URL
  : 'http://localhost:8000/api/v1'

export class ExerciseApiError extends Error {
  public status?: number

  constructor(message: string, status?: number) {
    super(message)
    this.name = 'ExerciseApiError'
    this.status = status
  }
}

export interface ExerciseFilterParams {
  muscle?: MuscleGroup | string
  equipment?: EquipmentType | string
  difficulty?: DifficultyLevel | string
  category?: string
  searchQuery?: string
}

export const exerciseService = {
  /**
   * Fetches exercises from FastAPI backend with query filtering.
   * Throws ExerciseApiError on failure. Returns legitimate empty array when no exercises match.
   */
  async getExercises(filters?: ExerciseFilterParams): Promise<Exercise[]> {
    const params = new URLSearchParams()
    if (filters?.muscle && filters.muscle !== 'All') {
      params.append('muscle', filters.muscle.toLowerCase())
    }
    if (filters?.equipment && filters.equipment !== 'All') {
      params.append('equipment', filters.equipment.toLowerCase().replace(/\s+/g, '_'))
    }
    if (filters?.difficulty && filters.difficulty !== 'All') {
      params.append('difficulty', filters.difficulty.toLowerCase())
    }
    if (filters?.category && filters.category !== 'All') {
      params.append('category', filters.category.toLowerCase())
    }
    if (filters?.searchQuery?.trim()) {
      params.append('search', filters.searchQuery.trim())
    }

    const queryString = params.toString()
    const url = `${API_BASE_URL}/exercises${queryString ? `?${queryString}` : ''}`

    try {
      const res = await fetch(url)
      if (!res.ok) {
        throw new ExerciseApiError(`Failed to fetch exercises (${res.status}): ${res.statusText}`, res.status)
      }
      const data = await res.json()
      if (!Array.isArray(data)) {
        throw new ExerciseApiError('Invalid response format: expected exercise list', res.status)
      }
      return data as Exercise[]
    } catch (err: any) {
      if (err instanceof ExerciseApiError) {
        throw err
      }
      throw new ExerciseApiError(err?.message || 'Network error fetching exercises')
    }
  },

  /**
   * Fetches single exercise details by ID.
   * Returns null on 404 or missing ID. Throws ExerciseApiError on network/server error.
   */
  async getExerciseById(id: string): Promise<Exercise | null> {
    if (!id || !id.trim()) {
      return null
    }

    try {
      const res = await fetch(`${API_BASE_URL}/exercises/${encodeURIComponent(id)}`)
      if (res.status === 404) {
        return null
      }
      if (!res.ok) {
        throw new ExerciseApiError(`Failed to fetch exercise (${res.status}): ${res.statusText}`, res.status)
      }
      return (await res.json()) as Exercise
    } catch (err: any) {
      if (err instanceof ExerciseApiError) {
        throw err
      }
      throw new ExerciseApiError(err?.message || `Network error fetching exercise ${id}`)
    }
  },
}

