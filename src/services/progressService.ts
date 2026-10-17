import type { ProgressSummary, ProgressDashboardData } from '../types'
import { getIdToken } from '../lib/firebase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export function createEmptyProgressDashboardData(): ProgressDashboardData {
  return {
    kpis: [
      { id: 'k1', title: 'Workout Sessions', value: '0', changePct: '0% vs previous', trendData: [0], color: '#10b981' },
      { id: 'k2', title: 'Total Volume', value: '0 kg', changePct: '0% vs previous', trendData: [0], color: '#3b82f6' },
      { id: 'k3', title: 'Calories Burned', value: '0 kcal', changePct: '0% vs previous', trendData: [0], color: '#f97316' },
      { id: 'k4', title: 'Avg. Workout Time', value: '0 min', changePct: '0% vs previous', trendData: [0], color: '#a855f7' },
      { id: 'k5', title: 'Consistency Streak', value: '0 Days', changePct: '0/7 days this week', trendData: [0], color: '#10b981' },
    ],
    strengthProgress: [],
    bodyComposition: {
      dateCompare: 'No measurements yet',
      weightKg: 0,
      weightChangeKg: 0,
      bodyFatPct: 0,
      bodyFatChangePct: 0,
      muscleMassKg: 0,
      muscleMassChangeKg: 0,
      bmi: 0,
      bmiChange: 0,
      goalProgressPct: 0,
      goalKgToGo: 0,
    },
    muscleGroupProgress: [],
    performanceTrends: [
      { name: 'STRENGTH', value: '—', status: 'Untracked', trendData: [0], iconName: 'dumbbell' },
      { name: 'ENDURANCE', value: '—', status: 'Untracked', trendData: [0], iconName: 'running' },
      { name: 'POWER', value: '—', status: 'Untracked', trendData: [0], iconName: 'lightning' },
      { name: 'CONSISTENCY', value: '—', status: 'Untracked', trendData: [0], iconName: 'target' },
    ],
    personalRecords: [],
    recentWorkouts: [],
    progressPhotos: [],
  }
}

export function createEmptyProgressSummary(): ProgressSummary {
  return {
    weeklyConsistencyDays: 0,
    streakDays: 0,
    weightHistory: [],
    personalRecords: [],
    workoutVolumeHistory: [],
    dashboardData: createEmptyProgressDashboardData(),
  }
}

export const progressService = {
  /**
   * Fetches the full dashboard payload for ProgressPage.
   */
  async getProgressDashboardData(period: string = '30d'): Promise<ProgressDashboardData> {
    const token = await getIdToken()
    if (token) {
      try {
        const res = await fetch(`${API_BASE_URL}/progress/dashboard?period=${period}`, {
          headers: { Authorization: `Bearer ${token}` },
        })
        if (res.ok) {
          const liveData = await res.json()
          if (liveData && liveData.kpis) {
            return liveData as ProgressDashboardData
          }
        }
      } catch (err) {
        console.warn('FastAPI /progress/dashboard unreachable:', err)
      }
    }

    return createEmptyProgressDashboardData()
  },

  /**
   * Fetches high-level progress summary and wraps dashboard data.
   */
  async getProgressSummary(period: string = '30d'): Promise<ProgressSummary> {
    const token = await getIdToken()
    if (token) {
      try {
        const [dashRes, sumRes] = await Promise.all([
          fetch(`${API_BASE_URL}/progress/dashboard?period=${period}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
          fetch(`${API_BASE_URL}/progress/summary?period=${period}`, {
            headers: { Authorization: `Bearer ${token}` },
          }),
        ])

        if (dashRes.ok && sumRes.ok) {
          const dashboard = (await dashRes.json()) as ProgressDashboardData
          const summary = await sumRes.json()

          return {
            weeklyConsistencyDays: summary.weeklyConsistencyDays ?? 0,
            streakDays: summary.currentStreakDays ?? 0,
            weightHistory:
              dashboard.bodyComposition?.weightKg && dashboard.bodyComposition.weightKg > 0
                ? [{ date: 'Current', weightKg: dashboard.bodyComposition.weightKg }]
                : [],
            personalRecords: (dashboard.personalRecords || []).map((pr) => ({
              exerciseId: pr.id,
              exerciseName: pr.exerciseName,
              weightKg: parseFloat(pr.value) || 0,
              reps: 1,
              achievedDate: pr.date,
            })),
            workoutVolumeHistory: (dashboard.strengthProgress || []).map((sp) => ({
              date: sp.date,
              volumeKg: sp.totalVolumeKg,
            })),
            dashboardData: dashboard,
          }
        }
      } catch (err) {
        console.warn('FastAPI /progress unreachable:', err)
      }
    }

    return createEmptyProgressSummary()
  },

  /**
   * Fetches progression history for a specific exercise.
   */
  async getExerciseProgression(exerciseId: string) {
    const token = await getIdToken()
    if (!token) return null

    try {
      const res = await fetch(`${API_BASE_URL}/progress/exercises/${exerciseId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        return await res.json()
      }
    } catch (err) {
      console.warn(`Error fetching progression for ${exerciseId}:`, err)
    }
    return null
  },

  /**
   * Fetches volume time series.
   */
  async getVolumeTimeSeries(period: string = '30d') {
    const token = await getIdToken()
    if (!token) return []

    try {
      const res = await fetch(`${API_BASE_URL}/progress/volume?period=${period}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        return await res.json()
      }
    } catch (err) {
      console.warn('Error fetching volume time series:', err)
    }
    return []
  },

  async logWeight(weightKg: number, _date?: string): Promise<ProgressSummary> {
    const token = await getIdToken()
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/users/me`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            personalStats: { weightKg },
          }),
        })
      } catch (err) {
        console.warn('Could not sync logged weight with user profile:', err)
      }
    }

    return this.getProgressSummary()
  },
}
