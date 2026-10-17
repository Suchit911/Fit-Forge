import type { NotificationsDashboardData } from '../types'
import { getIdToken } from '../lib/firebase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const fallbackNotificationsDashboardData: NotificationsDashboardData = {
  unreadCount: 0,
  todayCount: 0,
  weekCount: 0,
  importantCount: 0,
  notifications: [],
  insights: [],
  importantUpdates: [],
  preferences: {
    workoutReminders: true,
    achievementAlerts: true,
    nutritionReminders: true,
    aiCoachInsights: true,
    progressReports: true,
    marketingPromotions: false,
  },
}

/**
 * Derives local browser calendar date grouping and display time from authoritative createdAt ISO string.
 * This guarantees grouping reflects the user's actual browser day rather than server UTC day.
 */
export function deriveLocalGroupingAndTimestamp(createdAtIso?: string): {
  dateGroup: 'Today' | 'Yesterday' | 'Earlier'
  timestamp: string
} {
  if (!createdAtIso) {
    return { dateGroup: 'Earlier', timestamp: 'Recently' }
  }
  try {
    const itemDate = new Date(createdAtIso)
    const now = new Date()

    // Local day start boundaries in browser timezone
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const startOfYesterday = startOfToday - 86400000

    const itemTime = itemDate.getTime()
    const timeStr = itemDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

    if (itemTime >= startOfToday) {
      return { dateGroup: 'Today', timestamp: timeStr }
    } else if (itemTime >= startOfYesterday) {
      return { dateGroup: 'Yesterday', timestamp: `Yesterday, ${timeStr}` }
    } else {
      const dateStr = itemDate.toLocaleDateString([], { month: 'short', day: 'numeric' })
      return { dateGroup: 'Earlier', timestamp: dateStr }
    }
  } catch {
    return { dateGroup: 'Earlier', timestamp: 'Recently' }
  }
}

export const notificationsService = {
  /**
   * Fetches full notifications dashboard payload for current authenticated user.
   */
  async getNotificationsData(): Promise<NotificationsDashboardData> {
    const token = await getIdToken()
    if (!token) {
      return fallbackNotificationsDashboardData
    }

    try {
      const res = await fetch(`${API_BASE_URL}/notifications`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        const raw = (await res.json()) as NotificationsDashboardData
        // Project local browser date groups onto notifications
        const localizedNotifications = (raw.notifications || []).map((n) => {
          const { dateGroup, timestamp } = deriveLocalGroupingAndTimestamp(n.createdAt)
          return {
            ...n,
            dateGroup,
            timestamp: n.timestamp || timestamp,
          }
        })
        return {
          ...raw,
          notifications: localizedNotifications,
        }
      }
      return fallbackNotificationsDashboardData
    } catch (err) {
      console.warn('Failed to fetch notifications, falling back to clean initial state:', err)
      return fallbackNotificationsDashboardData
    }
  },

  /**
   * Lightweight query for unread notifications count (used for polling).
   */
  async getUnreadCount(): Promise<number> {
    const token = await getIdToken()
    if (!token) return 0

    try {
      const res = await fetch(`${API_BASE_URL}/notifications/unread-count`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = (await res.json()) as { unreadCount: number }
        return data.unreadCount ?? 0
      }
      return 0
    } catch {
      return 0
    }
  },

  /**
   * Marks a single notification as read.
   */
  async markAsRead(id: string): Promise<void> {
    const token = await getIdToken()
    if (!token) return

    const res = await fetch(`${API_BASE_URL}/notifications/${id}/read`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      throw new Error(`Failed to mark notification as read: HTTP ${res.status}`)
    }
  },

  /**
   * Marks all notifications as read.
   */
  async markAllAsRead(): Promise<{ unreadCount: number; markedCount: number }> {
    const token = await getIdToken()
    if (!token) return { unreadCount: 0, markedCount: 0 }

    const res = await fetch(`${API_BASE_URL}/notifications/read-all`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      throw new Error(`Failed to mark all notifications as read: HTTP ${res.status}`)
    }
    return (await res.json()) as { unreadCount: number; markedCount: number }
  },
}
