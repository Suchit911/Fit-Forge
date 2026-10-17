import { getIdToken } from '../lib/firebase.ts'
import type {
  SettingsDashboardData,
  GeneralSettingsData,
  NotificationSettingsData,
  AppearanceSettingsData,
  PrivacySettingsData,
  AICoachSettingsData,
} from '../types/index.ts'

const API_BASE_URL =
  typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL
    ? (import.meta as any).env.VITE_API_BASE_URL
    : 'http://localhost:8000/api/v1'

/**
 * Parses JSON error details from FastAPI error response.
 */
async function extractErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body?.detail === 'string') {
      return body.detail
    }
    if (Array.isArray(body?.detail)) {
      return body.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
    }
  } catch {
    // Ignore JSON parsing failure
  }
  return `${fallback} (HTTP ${res.status})`
}

export const settingsService = {
  _getIdToken: getIdToken,

  /**
   * Authenticated API helper for settings requests.
   * Uses the active Firebase ID token; rejects immediately if unauthenticated.
   */
  async fetchWithAuth(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const token = await this._getIdToken()
    if (!token) {
      throw new Error('Authentication required to access user settings')
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers as Record<string, string> | undefined),
    }

    try {
      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      })
      return res
    } catch (err: any) {
      throw new Error(`Network failure connecting to settings service: ${err.message || 'Connection failed'}`)
    }
  },

  /**
   * Retrieves authenticated user's settings from the FastAPI backend.
   * If user has not yet saved preferences, server returns deterministic first-read defaults.
   */
  async getSettingsData(): Promise<SettingsDashboardData> {
    const res = await this.fetchWithAuth('/settings', { method: 'GET' })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, 'Failed to fetch settings from server')
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Partially updates general settings.
   */
  async updateGeneralSettings(general: Partial<GeneralSettingsData>): Promise<SettingsDashboardData> {
    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ general }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, 'Failed to update general settings')
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Toggles an individual notification preference.
   */
  async toggleNotification(
    key: keyof NotificationSettingsData,
    currentValue?: boolean
  ): Promise<SettingsDashboardData> {
    let nextVal: boolean
    if (currentValue !== undefined) {
      nextVal = !currentValue
    } else {
      const current = await this.getSettingsData()
      nextVal = !current.notifications[key]
    }

    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({
        notifications: {
          [key]: nextVal,
        },
      }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, `Failed to toggle notification setting: ${key}`)
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Updates partial appearance settings.
   */
  async updateAppearanceSettings(appearance: Partial<AppearanceSettingsData>): Promise<SettingsDashboardData> {
    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ appearance }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, 'Failed to update appearance settings')
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Toggles an individual boolean appearance preference (e.g. darkMode, animations, reduceMotion).
   */
  async toggleAppearanceSetting(
    key: keyof AppearanceSettingsData,
    currentValue?: boolean
  ): Promise<SettingsDashboardData> {
    let nextVal: boolean
    if (currentValue !== undefined) {
      nextVal = !currentValue
    } else {
      const current = await this.getSettingsData()
      nextVal = !current.appearance[key]
    }

    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({
        appearance: {
          [key]: nextVal,
        },
      }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, `Failed to toggle appearance setting: ${key}`)
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Updates partial privacy & security settings.
   */
  async updatePrivacySettings(privacy: Partial<PrivacySettingsData>): Promise<SettingsDashboardData> {
    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ privacy }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, 'Failed to update privacy settings')
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Updates partial AI Coach preferences.
   */
  async updateAICoachSettings(aiCoach: Partial<AICoachSettingsData>): Promise<SettingsDashboardData> {
    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ aiCoach }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, 'Failed to update AI Coach settings')
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Resets AI Coach settings to recommended baseline defaults on backend.
   */
  async resetAICoachDefaults(): Promise<SettingsDashboardData> {
    const defaults: AICoachSettingsData = {
      personality: 'Motivational',
      intensity: 'High',
      focus: 'Muscle Gain',
      workoutRecommendations: 'Advanced',
      nutritionRecommendations: 'Personalized',
      formAnalysisInsights: 'Detailed',
    }

    const res = await this.fetchWithAuth('/settings', {
      method: 'PATCH',
      body: JSON.stringify({ aiCoach: defaults }),
    })
    if (!res.ok) {
      const msg = await extractErrorMessage(res, 'Failed to reset AI Coach settings')
      throw new Error(msg)
    }
    return (await res.json()) as SettingsDashboardData
  },

  /**
   * Hardware Device Sync Connection.
   * External wearable integrations are currently unsupported in this environment.
   * Rejects immediately to prevent advertising unoperational integrations as connected.
   */
  async toggleDeviceConnection(deviceId: string): Promise<SettingsDashboardData> {
    void deviceId
    throw new Error(
      'External wearable integration is not configured. Third-party device synchronization is currently unsupported.'
    )
  },
}
