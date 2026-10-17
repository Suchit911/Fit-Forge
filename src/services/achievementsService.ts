import type { Achievement, AchievementsDashboardData } from '../types'
import { getIdToken } from '../lib/firebase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const fallbackAchievementsDashboardData: AchievementsDashboardData = {
  kpis: [
    { id: 'k1', title: 'Total Achievements', value: '0', supportingText: '0 of 24 unlocked', iconName: 'trophy', color: '#10b981' },
    { id: 'k2', title: 'Total Points', value: '0', supportingText: '1,000 pts to Level 10', iconName: 'sun', color: '#f59e0b' },
    { id: 'k3', title: 'Longest Streak', value: '0 Days', supportingText: 'Current: 0 Days', iconName: 'flame', color: '#3b82f6' },
    { id: 'k4', title: 'Challenges Completed', value: '0', supportingText: 'No active challenges', iconName: 'target', color: '#a855f7' },
    { id: 'k5', title: 'Rewards Earned', value: '0', supportingText: 'Milestone badges', iconName: 'gift', color: '#f97316' },
  ],
  recentAchievements: [],
  progressSummary: {
    overallPct: 0,
    achievedCount: 0,
    inProgressCount: 0,
    lockedCount: 24,
    nextMilestone: {
      level: 10,
      title: 'Novice Lifter',
      description: 'Earn 1,000 total points',
      currentPts: 0,
      targetPts: 1000,
      ptsToGo: 1000,
      currentLevel: 1,
    },
  },
  categories: [
    { id: 'c1', title: 'Workout Mastery', current: 0, total: 5, pct: 0, iconName: 'dumbbell', color: '#10b981' },
    { id: 'c2', title: 'Consistency', current: 0, total: 4, pct: 0, iconName: 'calendar', color: '#a855f7' },
    { id: 'c3', title: 'Strength', current: 0, total: 7, pct: 0, iconName: 'biceps', color: '#f59e0b' },
    { id: 'c4', title: 'Endurance', current: 0, total: 3, pct: 0, iconName: 'running', color: '#3b82f6' },
    { id: 'c5', title: 'Nutrition', current: 0, total: 4, pct: 0, iconName: 'apple', color: '#10b981' },
    { id: 'c6', title: 'Special', current: 0, total: 1, pct: 0, iconName: 'star', color: '#06b6d4' },
  ],
  currentChallenges: [],
  leaderboard: [],
}

export const achievementsService = {
  /**
   * Fetches full data-driven achievements dashboard for current authenticated user.
   */
  async getDashboardData(): Promise<AchievementsDashboardData> {
    const token = await getIdToken()
    if (!token) {
      return fallbackAchievementsDashboardData
    }

    try {
      const res = await fetch(`${API_BASE_URL}/achievements`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        return (await res.json()) as AchievementsDashboardData
      }
      console.warn(`Achievements API returned status ${res.status}, falling back to clean initial state`)
    } catch (err) {
      console.warn('Error fetching achievements dashboard:', err)
    }

    return fallbackAchievementsDashboardData
  },

  /**
   * Fetches full list of achievement definitions with user progress.
   */
  async getAchievements(category?: string): Promise<Achievement[]> {
    const token = await getIdToken()
    if (!token) return []

    try {
      const url = category
        ? `${API_BASE_URL}/achievements/list?category=${encodeURIComponent(category)}`
        : `${API_BASE_URL}/achievements/list`

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        const data = await res.json()
        return data.map((item: any) => ({
          id: item.id,
          title: item.title,
          description: item.description,
          iconName: item.iconName,
          unlockedAt: item.unlockedAt || undefined,
          progressPercentage: item.progressPercentage,
          isUnlocked: item.isUnlocked,
          category: item.category,
          points: item.points,
          currentValue: item.currentValue,
          targetValue: item.targetValue,
          unit: item.unit,
        }))
      }
    } catch (err) {
      console.warn('Error fetching achievement list:', err)
    }

    return []
  },

  /**
   * Creates a user-scoped custom achievement milestone and returns updated dashboard.
   */
  async addCustomAchievement(name: string, description: string, category: string): Promise<AchievementsDashboardData> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('User is not authenticated')
    }

    const res = await fetch(`${API_BASE_URL}/achievements/custom`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name,
        description,
        category,
      }),
    })

    if (!res.ok) {
      const errText = await res.text()
      throw new Error(`Failed to create custom milestone: ${res.status} ${errText}`)
    }

    return (await res.json()) as AchievementsDashboardData
  },

  /**
   * Acknowledges and clears the isNew flag for all newly unlocked achievements.
   */
  async clearNewAchievements(): Promise<void> {
    const token = await getIdToken()
    if (!token) return

    try {
      await fetch(`${API_BASE_URL}/achievements/clear-new`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch (err) {
      console.warn('Error clearing new achievements:', err)
    }
  },
}
