import React, { useState } from 'react'
import { useSettings } from '../../hooks'
import { SettingsHeader } from '../../components/settings/SettingsHeader'
import { SettingsTabs } from '../../components/settings/SettingsTabs'
import { GeneralSettingsCard } from '../../components/settings/GeneralSettingsCard'
import { NotificationSettingsCard } from '../../components/settings/NotificationSettingsCard'
import { AppearanceSettingsCard } from '../../components/settings/AppearanceSettingsCard'
import { PrivacySecurityCard } from '../../components/settings/PrivacySecurityCard'
import { ConnectedDevicesCard } from '../../components/settings/ConnectedDevicesCard'
import { AICoachSettingsCard } from '../../components/settings/AICoachSettingsCard'
import { DataManagementCard } from '../../components/settings/DataManagementCard'
import { DangerZoneCard } from '../../components/settings/DangerZoneCard'
import { SettingsModal } from '../../components/settings/SettingsModal'
import { Skeleton, ErrorState } from '../../components/ui'

export const SettingsPage: React.FC = () => {
  const {
    settings,
    isLoading,
    isError,
    refetch,
    isUpdating,
    mutationError,
    updateGeneral,
    updateAppearance,
    updatePrivacy,
    toggleNotification,
    toggleAppearance,
    toggleDevice,
    updateAICoach,
    resetAICoach,
  } = useSettings()

  const [activeTab, setActiveTab] = useState('General')
  const [modalConfig, setModalConfig] = useState<{
    isOpen: boolean
    title: string
    description: string
    confirmText?: string
    isDanger?: boolean
  }>({
    isOpen: false,
    title: '',
    description: '',
  })

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError || !settings) {
    return (
      <ErrorState
        title="Settings Data Unavailable"
        message="Could not load application configuration settings. Please try again."
        onRetry={refetch}
      />
    )
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <SettingsHeader />

      {/* Sub-Header Navigation Tabs */}
      <SettingsTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Persistence or Mutation Error Notice */}
      {mutationError && (
        <div
          role="alert"
          className="rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-xs font-mono text-red-400"
        >
          Failed to save settings: {(mutationError as any).message || 'Server error'}
        </div>
      )}

      {/* Updating indicator */}
      {isUpdating && (
        <div className="flex items-center gap-2 text-xs font-mono text-emerald-400">
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Syncing settings to server...</span>
        </div>
      )}

      {/* Upper Row: 4 Equal Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <GeneralSettingsCard
          general={settings.general}
          onUpdate={(data) => updateGeneral(data)}
        />
        <NotificationSettingsCard
          notifications={settings.notifications}
          onToggle={(k) => toggleNotification(k)}
          onManageClick={() =>
            setModalConfig({
              isOpen: true,
              title: 'Notification Preferences',
              description: 'Configure frequency and channels for your workout and AI alerts.',
            })
          }
        />
        <AppearanceSettingsCard
          appearance={settings.appearance}
          onToggle={(k) => toggleAppearance(k)}
          onUpdate={(data) => updateAppearance(data)}
          onPreviewClick={() =>
            setModalConfig({
              isOpen: true,
              title: 'Preview Theme Changes',
              description: 'Your accent and contrast density settings will be applied immediately across all screens.',
            })
          }
        />
        <PrivacySecurityCard
          privacy={settings.privacy}
          onToggleAi={() => updatePrivacy({ aiAnalysisData: !settings.privacy.aiAnalysisData })}
          onUpdate={(data) => updatePrivacy(data)}
          onActionClick={(act) =>
            setModalConfig({
              isOpen: true,
              title: act,
              description: `Manage your security settings for ${act}.`,
            })
          }
        />
      </div>

      {/* Lower Row: 3 Columns (4, 4, 4) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Connected Devices (4 of 12 cols) */}
        <div className="lg:col-span-4">
          <ConnectedDevicesCard
            devices={settings.devices}
            onToggleConnection={async (id) => {
              try {
                await toggleDevice(id)
              } catch (err: any) {
                setModalConfig({
                  isOpen: true,
                  title: 'Device Sync Not Supported',
                  description:
                    err.message ||
                    'Third-party external wearable synchronization is not supported in this environment.',
                })
              }
            }}
            onManageClick={() =>
              setModalConfig({
                isOpen: true,
                title: 'Connected Fitness Devices',
                description:
                  'External hardware wearable synchronization is not configured in this environment.',
              })
            }
          />
        </div>

        {/* AI Coach Settings (4 of 12 cols) */}
        <div className="lg:col-span-4">
          <AICoachSettingsCard
            aiCoach={settings.aiCoach}
            onUpdate={(data) => updateAICoach(data)}
            onReset={() => resetAICoach()}
          />
        </div>

        {/* Right Stack: Data & Management + Danger Zone (4 of 12 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <DataManagementCard
            onExportClick={() =>
              setModalConfig({
                isOpen: true,
                title: 'Export Fitness Data',
                description: 'Download a full JSON/CSV export of all your workouts, nutrition logs, and body metrics.',
                confirmText: 'Download Export',
              })
            }
            onClearClick={() =>
              setModalConfig({
                isOpen: true,
                title: 'Clear Activity Data',
                description: 'Are you sure you want to clear your workout history? This action cannot be undone.',
                confirmText: 'Clear Data',
                isDanger: true,
              })
            }
            onResetOnboardingClick={() =>
              setModalConfig({
                isOpen: true,
                title: 'Reset Onboarding Questionnaire',
                description: 'This will reset your fitness baseline and allow you to retake the initial assessment.',
                confirmText: 'Reset Baseline',
              })
            }
          />

          <DangerZoneCard
            onDeleteAccountClick={() =>
              setModalConfig({
                isOpen: true,
                title: 'Delete Account',
                description: 'Permanently delete your AI FITNESS account, progress data, and subscriptions. This action is irreversible.',
                confirmText: 'Permanently Delete',
                isDanger: true,
              })
            }
          />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={modalConfig.isOpen}
        onClose={() => setModalConfig({ ...modalConfig, isOpen: false })}
        title={modalConfig.title}
        description={modalConfig.description}
        confirmText={modalConfig.confirmText}
        isDanger={modalConfig.isDanger}
      />
    </div>
  )
}
