import React, { useState } from 'react'
import { useAchievements } from '../../hooks'
import { AchievementsHeader } from '../../components/achievements/AchievementsHeader'
import { AchievementsTabs } from '../../components/achievements/AchievementsTabs'
import { AchievementKpiStrip } from '../../components/achievements/AchievementKpiStrip'
import { RecentAchievementsSection } from '../../components/achievements/RecentAchievementsSection'
import { AchievementsProgressCard } from '../../components/achievements/AchievementsProgressCard'
import { AchievementCategoriesSection } from '../../components/achievements/AchievementCategoriesSection'
import { CurrentChallengesSection } from '../../components/achievements/CurrentChallengesSection'
import { LeaderboardCard } from '../../components/achievements/LeaderboardCard'
import { AchievementAddModal } from '../../components/achievements/AchievementAddModal'
import { Skeleton, ErrorState } from '../../components/ui'

export const AchievementsPage: React.FC = () => {
  const { dashboardData, isLoading, isError, refetch } = useAchievements()

  const [activeTab, setActiveTab] = useState('Overview')
  const [currentFilter] = useState('All Time')
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError || !dashboardData) {
    return (
      <ErrorState
        title="Achievements Data Unavailable"
        message="Could not load achievements summary. Please try again."
        onRetry={refetch}
      />
    )
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <AchievementsHeader onAddAchievementClick={() => setIsAddModalOpen(true)} />

      {/* Navigation Tabs & Date/Filter Selector */}
      <AchievementsTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        currentFilter={currentFilter}
      />

      {/* KPI Metric Strip (5 Horizontal Cards) */}
      <AchievementKpiStrip kpis={dashboardData.kpis} />

      {/* Row 1: Recent Achievements & Achievements Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <RecentAchievementsSection badges={dashboardData.recentAchievements} />
        </div>
        <div className="lg:col-span-4">
          <AchievementsProgressCard progress={dashboardData.progressSummary} />
        </div>
      </div>

      {/* Row 2: Achievement Categories & Leaderboards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <AchievementCategoriesSection categories={dashboardData.categories} />
        </div>
        <div className="lg:col-span-4">
          <LeaderboardCard users={dashboardData.leaderboard} />
        </div>
      </div>

      {/* Row 3: Current Challenges */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <CurrentChallengesSection challenges={dashboardData.currentChallenges} />
        </div>
      </div>

      {/* Add Custom Achievement Modal */}
      <AchievementAddModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={refetch}
      />
    </div>
  )
}
