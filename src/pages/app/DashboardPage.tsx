import React from 'react'
import { DashboardHeader } from '../../components/dashboard/DashboardHeader'
import { MetricOverview } from '../../components/dashboard/MetricOverview'
import { TodayWorkoutCard } from '../../components/dashboard/TodayWorkoutCard'
import { DailyNutritionCard } from '../../components/dashboard/DailyNutritionCard'
import { CalendarScheduleCard } from '../../components/dashboard/CalendarScheduleCard'
import { ProgressOverviewCard } from '../../components/dashboard/ProgressOverviewCard'
import { RecentAchievementsCard } from '../../components/dashboard/RecentAchievementsCard'
import { AICoachCard } from '../../components/dashboard/AICoachCard'
import { ActivitySummary } from '../../components/dashboard/ActivitySummary'

export const DashboardPage: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Top Header */}
      <DashboardHeader />

      {/* Top 4 Metric Cards */}
      <MetricOverview />

      {/* Main Multi-Column Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (8 of 12 columns on desktop) */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Row 1: Today's Workout & Daily Nutrition */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
            <div className="md:col-span-7">
              <TodayWorkoutCard />
            </div>
            <div className="md:col-span-5">
              <DailyNutritionCard />
            </div>
          </div>

          {/* Row 2: Progress Overview & Recent Achievements */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <ProgressOverviewCard />
            <RecentAchievementsCard />
          </div>

          {/* Row 3: Today's Activity Summary */}
          <ActivitySummary />

        </div>

        {/* Right Column (4 of 12 columns on desktop) */}
        <div className="lg:col-span-4 space-y-6">
          <CalendarScheduleCard />
          <AICoachCard />
        </div>

      </div>
    </div>
  )
}
