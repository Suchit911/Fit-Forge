import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsService } from '../services'
import type {
  GeneralSettingsData,
  NotificationSettingsData,
  AppearanceSettingsData,
  PrivacySettingsData,
  AICoachSettingsData,
} from '../types'

export function useSettings() {
  const queryClient = useQueryClient()

  const settingsQuery = useQuery({
    queryKey: ['settingsData'],
    queryFn: () => settingsService.getSettingsData(),
  })

  const updateGeneralMutation = useMutation({
    mutationFn: (data: Partial<GeneralSettingsData>) => settingsService.updateGeneralSettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const updateAppearanceMutation = useMutation({
    mutationFn: (data: Partial<AppearanceSettingsData>) => settingsService.updateAppearanceSettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const updatePrivacyMutation = useMutation({
    mutationFn: (data: Partial<PrivacySettingsData>) => settingsService.updatePrivacySettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const toggleNotificationMutation = useMutation({
    mutationFn: (key: keyof NotificationSettingsData) => {
      const current = settingsQuery.data?.notifications?.[key]
      return settingsService.toggleNotification(key, current)
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const toggleAppearanceMutation = useMutation({
    mutationFn: (key: keyof AppearanceSettingsData) => {
      const current = settingsQuery.data?.appearance?.[key]
      return settingsService.toggleAppearanceSetting(key, typeof current === 'boolean' ? current : undefined)
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const toggleDeviceMutation = useMutation({
    mutationFn: (deviceId: string) => settingsService.toggleDeviceConnection(deviceId),
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const updateAICoachMutation = useMutation({
    mutationFn: (data: Partial<AICoachSettingsData>) => settingsService.updateAICoachSettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const resetAICoachMutation = useMutation({
    mutationFn: () => settingsService.resetAICoachDefaults(),
    onSuccess: (data) => {
      queryClient.setQueryData(['settingsData'], data)
    },
  })

  const isUpdating =
    updateGeneralMutation.isPending ||
    updateAppearanceMutation.isPending ||
    updatePrivacyMutation.isPending ||
    toggleNotificationMutation.isPending ||
    toggleAppearanceMutation.isPending ||
    toggleDeviceMutation.isPending ||
    updateAICoachMutation.isPending ||
    resetAICoachMutation.isPending

  const mutationError =
    updateGeneralMutation.error ||
    updateAppearanceMutation.error ||
    updatePrivacyMutation.error ||
    toggleNotificationMutation.error ||
    toggleAppearanceMutation.error ||
    toggleDeviceMutation.error ||
    updateAICoachMutation.error ||
    resetAICoachMutation.error

  return {
    settings: settingsQuery.data,
    isLoading: settingsQuery.isLoading,
    isError: settingsQuery.isError,
    error: settingsQuery.error,
    refetch: settingsQuery.refetch,
    isUpdating,
    mutationError,
    updateGeneral: updateGeneralMutation.mutateAsync,
    updateAppearance: updateAppearanceMutation.mutateAsync,
    updatePrivacy: updatePrivacyMutation.mutateAsync,
    toggleNotification: toggleNotificationMutation.mutateAsync,
    toggleAppearance: toggleAppearanceMutation.mutateAsync,
    toggleDevice: toggleDeviceMutation.mutateAsync,
    updateAICoach: updateAICoachMutation.mutateAsync,
    resetAICoach: resetAICoachMutation.mutateAsync,
  }
}
