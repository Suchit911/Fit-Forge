/**
 * REAL-DATA REMEDIATION — STAGE 5 TEST SUITE
 * Persistent User Settings Frontend Verification
 *
 * Verifies:
 * 1. Loading settings from the authenticated API.
 * 2. Updating individual settings using PATCH.
 * 3. Preserving unrelated settings during partial updates.
 * 4. Handling validation and API errors without false successes.
 * 5. Showing success only after confirmed server persistence.
 * 6. Avoiding false saved state when the API call fails.
 * 7. Reloading settings and rendering returned server values.
 * 8. Rejecting fake device connections for unsupported hardware integrations.
 * 9. Enforcing Bearer authentication on settings API requests.
 */

import { test, describe, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'

import { settingsService } from '../../src/services/settingsService.ts'
import type { SettingsDashboardData } from '../../src/types/index.ts'

describe('Stage 5 — Persistent User Settings Frontend Suite', () => {
  const originalGetIdToken = settingsService._getIdToken
  const originalFetch = globalThis.fetch

  const mockServerSettings: SettingsDashboardData = {
    userId: 'usr_test_stage5_athlete',
    persisted: true,
    updatedAt: '2026-10-17T10:00:00.000Z',
    general: {
      language: 'English',
      units: 'Metric (kg, cm)',
      timeZone: '(GMT+05:30) Asia/Kolkata',
      weekStartDay: 'Monday',
      defaultWorkoutDurationMin: 60,
    },
    notifications: {
      workoutReminders: true,
      restTimerAlerts: true,
      achievementNotifications: true,
      nutritionReminders: true,
      aiCoachInsights: true,
      weeklyProgressReport: true,
    },
    appearance: {
      darkMode: true,
      accentColor: 'Emerald Green',
      accentIntensity: 'Medium',
      uiDensity: 'Comfortable',
      animations: true,
      reduceMotion: false,
    },
    privacy: {
      profileVisibility: 'Public',
      workoutDataVisibility: 'Only You',
      progressPhotosVisibility: 'Only You',
      aiAnalysisData: true,
      twoFactorEnabled: true,
    },
    devices: [
      { id: 'dev_1', name: 'Apple Watch', description: 'Sync workouts & heart rate', isConnected: false, iconName: 'watch' },
      { id: 'dev_2', name: 'Fitbit', description: 'Sync activity & sleep data', isConnected: false, iconName: 'activity' },
      { id: 'dev_3', name: 'Google Fit', description: 'Sync health & activity', isConnected: false, iconName: 'heart' },
      { id: 'dev_4', name: 'Heart Rate Monitor', description: 'Sync heart rate data', isConnected: false, iconName: 'activity' },
      { id: 'dev_5', name: 'Smart Scale', description: 'Track weight & body metrics', isConnected: false, iconName: 'scale' },
    ],
    aiCoach: {
      personality: 'Motivational',
      intensity: 'High',
      focus: 'Muscle Gain',
      workoutRecommendations: 'Advanced',
      nutritionRecommendations: 'Personalized',
      formAnalysisInsights: 'Detailed',
    },
  }

  beforeEach(() => {
    settingsService._getIdToken = async () => 'mock-valid-firebase-token'
  })

  afterEach(() => {
    settingsService._getIdToken = originalGetIdToken
    globalThis.fetch = originalFetch
  })

  // 1. Loading settings from API
  test('1. Loads actual settings from GET /api/v1/settings with Bearer token', async () => {
    let capturedUrl = ''
    let capturedMethod = ''
    let capturedAuth = ''

    globalThis.fetch = (async (url: any, init: any) => {
      capturedUrl = String(url)
      capturedMethod = init?.method || 'GET'
      capturedAuth = init?.headers?.Authorization || ''
      return {
        ok: true,
        status: 200,
        json: async () => mockServerSettings,
      }
    }) as any

    const data = await settingsService.getSettingsData()

    assert.ok(capturedUrl.endsWith('/settings'))
    assert.equal(capturedMethod, 'GET')
    assert.equal(capturedAuth, 'Bearer mock-valid-firebase-token')
    assert.equal(data.userId, 'usr_test_stage5_athlete')
    assert.equal(data.general.language, 'English')
    assert.equal(data.notifications.workoutReminders, true)
    assert.equal(data.persisted, true)
  })

  // 2. Unauthenticated request rejection
  test('2. Rejects immediately when user is unauthenticated (token null)', async () => {
    settingsService._getIdToken = async () => null

    await assert.rejects(
      async () => settingsService.getSettingsData(),
      { message: /Authentication required/ }
    )
  })

  // 3. Updating individual settings using PATCH
  test('3. Sends partial PATCH to /api/v1/settings when updating general settings', async () => {
    let capturedUrl = ''
    let capturedMethod = ''
    let capturedBody: any = null

    globalThis.fetch = (async (url: any, init: any) => {
      capturedUrl = String(url)
      capturedMethod = init?.method || 'GET'
      capturedBody = JSON.parse(init?.body || '{}')
      return {
        ok: true,
        status: 200,
        json: async () => ({
          ...mockServerSettings,
          general: { ...mockServerSettings.general, ...capturedBody.general },
        }),
      }
    }) as any

    const updated = await settingsService.updateGeneralSettings({ units: 'Imperial (lbs, in)' })

    assert.ok(capturedUrl.endsWith('/settings'))
    assert.equal(capturedMethod, 'PATCH')
    assert.deepEqual(capturedBody, { general: { units: 'Imperial (lbs, in)' } })
    assert.equal(updated.general.units, 'Imperial (lbs, in)')
    // Other fields in general remain intact
    assert.equal(updated.general.language, 'English')
  })

  // 4. Preserving unrelated settings during partial updates
  test('4. Preserves unrelated settings sections during partial updates', async () => {
    globalThis.fetch = (async (_url: any, init: any) => {
      const body = JSON.parse(init?.body || '{}')
      return {
        ok: true,
        status: 200,
        json: async () => ({
          ...mockServerSettings,
          appearance: { ...mockServerSettings.appearance, ...body.appearance },
        }),
      }
    }) as any

    const updated = await settingsService.updateAppearanceSettings({ accentColor: 'Ocean Blue' })

    assert.equal(updated.appearance.accentColor, 'Ocean Blue')
    // Unrelated sections untouched
    assert.equal(updated.general.language, 'English')
    assert.equal(updated.notifications.workoutReminders, true)
    assert.equal(updated.privacy.profileVisibility, 'Public')
    assert.equal(updated.aiCoach.personality, 'Motivational')
  })

  // 5. Toggle individual notification setting
  test('5. Toggles notification setting by sending inverted value to PATCH', async () => {
    let capturedBody: any = null

    globalThis.fetch = (async (_url: any, init: any) => {
      capturedBody = JSON.parse(init?.body || '{}')
      return {
        ok: true,
        status: 200,
        json: async () => ({
          ...mockServerSettings,
          notifications: {
            ...mockServerSettings.notifications,
            ...capturedBody.notifications,
          },
        }),
      }
    }) as any

    const updated = await settingsService.toggleNotification('workoutReminders', true)
    assert.deepEqual(capturedBody, {
      notifications: { workoutReminders: false },
    })
    assert.equal(updated.notifications.workoutReminders, false)
  })

  // 6. Validation error from backend
  test('6. Surfaces backend validation error (422) explicitly', async () => {
    globalThis.fetch = (async () => ({
      ok: false,
      status: 422,
      json: async () => ({
        detail: [
          { loc: ['body', 'general', 'units'], msg: 'Input should be Metric (kg, cm) or Imperial (lbs, in)' },
        ],
      }),
    })) as any

    await assert.rejects(
      async () => settingsService.updateGeneralSettings({ units: 'Stone' as any }),
      { message: /Input should be Metric/ }
    )
  })

  // 7. Persistence failure handling (500)
  test('7. Fails gracefully and throws explicit error when persistence backend fails (500)', async () => {
    globalThis.fetch = (async () => ({
      ok: false,
      status: 500,
      json: async () => ({
        detail: 'Failed to persist user settings update.',
      }),
    })) as any

    await assert.rejects(
      async () => settingsService.updatePrivacySettings({ profileVisibility: 'Private' }),
      { message: /Failed to persist user settings update/ }
    )
  })

  // 8. Network failure handling
  test('8. Network drop throws explicit network connection error', async () => {
    globalThis.fetch = (async () => {
      throw new TypeError('Failed to fetch')
    }) as any

    await assert.rejects(
      async () => settingsService.getSettingsData(),
      { message: /Network failure connecting to settings service/ }
    )
  })

  // 9. Rejects fake device connections for unsupported integrations
  test('9. Rejects attempting to toggle unsupported external device integrations', async () => {
    await assert.rejects(
      async () => settingsService.toggleDeviceConnection('dev_1'),
      { message: /External wearable integration is not configured/ }
    )
  })

  // 10. Reset AI coach settings to baseline defaults
  test('10. resetAICoachDefaults sends complete recommended AI baseline to backend', async () => {
    let capturedBody: any = null

    globalThis.fetch = (async (_url: any, init: any) => {
      capturedBody = JSON.parse(init?.body || '{}')
      return {
        ok: true,
        status: 200,
        json: async () => ({
          ...mockServerSettings,
          aiCoach: capturedBody.aiCoach,
        }),
      }
    }) as any

    const res = await settingsService.resetAICoachDefaults()
    assert.equal(capturedBody.aiCoach.personality, 'Motivational')
    assert.equal(capturedBody.aiCoach.intensity, 'High')
    assert.equal(capturedBody.aiCoach.focus, 'Muscle Gain')
    assert.equal(capturedBody.aiCoach.workoutRecommendations, 'Advanced')
    assert.equal(res.aiCoach.personality, 'Motivational')
  })
})
