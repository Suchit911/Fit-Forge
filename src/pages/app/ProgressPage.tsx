import React, { useState } from 'react'
import { useProgress } from '../../hooks'
import { ProgressHeader } from '../../components/progress/ProgressHeader'
import { ProgressTabs } from '../../components/progress/ProgressTabs'
import { ProgressKpiStrip } from '../../components/progress/ProgressKpiStrip'
import { StrengthProgressChart } from '../../components/progress/StrengthProgressChart'
import { BodyCompositionCard } from '../../components/progress/BodyCompositionCard'
import { MuscleGroupProgressCard } from '../../components/progress/MuscleGroupProgressCard'
import { PerformanceTrendsCard } from '../../components/progress/PerformanceTrendsCard'
import { PersonalRecordsCard } from '../../components/progress/PersonalRecordsCard'
import { RecentWorkoutsTable } from '../../components/progress/RecentWorkoutsTable'
import { ProgressPhotosCard } from '../../components/progress/ProgressPhotosCard'
import { Skeleton, ErrorState } from '../../components/ui'

export const ProgressPage: React.FC = () => {
  const { progress, isLoading, isError, refetch } = useProgress()

  const [activeTab, setActiveTab] = useState('Overview')
  const [currentDateRange] = useState('Apr 12 - May 12, 2025')

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

  if (isError || !progress || !progress.dashboardData) {
    return (
      <ErrorState
        title="Progress Data Unavailable"
        message="Could not load progress dashboard. Please try again."
        onRetry={refetch}
      />
    )
  }

  const data = progress.dashboardData

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <ProgressHeader onShareClick={() => alert('Progress report shared!')} />

      {/* Tabs & Date Range Selector */}
      <ProgressTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        currentDateRange={currentDateRange}
      />

      {/* Top 5 KPI Metric Cards */}
      <ProgressKpiStrip kpis={data.kpis} />

      {/* Row 1: Strength Progress Chart & Body Composition */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8">
          <StrengthProgressChart data={data.strengthProgress} />
        </div>
        <div className="lg:col-span-4">
          <BodyCompositionCard stats={data.bodyComposition} />
        </div>
      </div>

      {/* Row 2: Muscle Group Progress, Performance Trends & Personal Records */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MuscleGroupProgressCard groups={data.muscleGroupProgress} />
        <PerformanceTrendsCard trends={data.performanceTrends} />
        <PersonalRecordsCard records={data.personalRecords} />
      </div>

      {/* Row 3: Recent Workouts & Progress Photos */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-6">
          <RecentWorkoutsTable workouts={data.recentWorkouts} />
        </div>
        <div className="lg:col-span-6">
          <ProgressPhotosCard photos={data.progressPhotos} />
        </div>
      </div>
    </div>
  )
}
