import React from 'react'
import { useNotifications } from '../../hooks'
import { NotificationsHeader } from '../../components/notifications/NotificationsHeader'
import { NotificationSummaryStrip } from '../../components/notifications/NotificationSummaryStrip'
import { NotificationFilters } from '../../components/notifications/NotificationFilters'
import { NotificationFeed } from '../../components/notifications/NotificationFeed'
import { NotificationInsightsCard } from '../../components/notifications/NotificationInsightsCard'
import { ImportantUpdatesCard } from '../../components/notifications/ImportantUpdatesCard'
import { NotificationPreferencesCard } from '../../components/notifications/NotificationPreferencesCard'
import { Skeleton, ErrorState } from '../../components/ui'

export const NotificationsPage: React.FC = () => {
  const {
    notificationsData,
    filteredNotifications,
    isLoading,
    isError,
    refetch,
    activeFilter,
    setActiveFilter,
    markAsRead,
    markAllAsRead,
  } = useNotifications()

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError || !notificationsData) {
    return (
      <ErrorState
        title="Notifications Unavailable"
        message="Could not load notification activity feed. Please try again."
        onRetry={refetch}
      />
    )
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <NotificationsHeader unreadCount={notificationsData.unreadCount} />

      {/* KPI Summary Strip */}
      <NotificationSummaryStrip
        unreadCount={notificationsData.unreadCount}
        todayCount={notificationsData.todayCount}
        weekCount={notificationsData.weekCount}
        importantCount={notificationsData.importantCount}
      />

      {/* Filter / Control Bar */}
      <NotificationFilters
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        onMarkAllAsRead={() => markAllAsRead()}
      />

      {/* Main Two-Column Layout (8 cols & 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Main Notification Feed (8 of 12 cols) */}
        <div className="lg:col-span-8">
          <NotificationFeed
            notifications={filteredNotifications}
            onMarkAsRead={(id) => markAsRead(id)}
          />
        </div>

        {/* Right Supporting Column (4 of 12 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <NotificationInsightsCard insights={notificationsData.insights} />
          <ImportantUpdatesCard updates={notificationsData.importantUpdates} />
          <NotificationPreferencesCard initialPrefs={notificationsData.preferences} />
        </div>
      </div>
    </div>
  )
}
