import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { WorkoutsHeader } from '../../components/workout/WorkoutsHeader'
import { WorkoutsFilterTabs } from '../../components/workout/WorkoutsFilterTabs'
import { FeaturedWorkoutsSection } from '../../components/workout/FeaturedWorkoutsSection'
import { WorkoutsTableList } from '../../components/workout/WorkoutsTableList'
import { WorkoutsRightPanel } from '../../components/workout/WorkoutsRightPanel'
import { WorkoutPlanGenerator } from '../../components/workout/plan/WorkoutPlanGenerator'
import { ActiveProgramView } from '../../components/workout/ActiveProgramView'
import { resolveActiveTabFromParam } from '../../utils/activeProgramOverview.ts'
import { useWorkouts } from '../../hooks'
import { Skeleton, ErrorState } from '../../components/ui'

export const WorkoutsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const [localTab, setLocalTab] = useState('All Workouts')
  const { workouts, isLoading, isError, refetchWorkouts } = useWorkouts()

  const tabParam = searchParams.get('tab')
  const activeTab = resolveActiveTabFromParam(tabParam, localTab)

  const handleTabChange = (tab: string) => {
    if (tab === 'Active Program') {
      setSearchParams({ tab: 'program' })
    } else if (tab === 'Generate Plan') {
      setSearchParams({ tab: 'generate' })
    } else {
      setSearchParams({})
      setLocalTab(tab)
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <WorkoutsHeader onGenerateClick={() => handleTabChange('Generate Plan')} />

      {/* Filter Tabs */}
      <WorkoutsFilterTabs activeTab={activeTab} onTabChange={handleTabChange} />

      {/* View Switch: Active Program vs Deterministic Plan Generator vs Standard Library */}
      {activeTab === 'Active Program' ? (
        <ActiveProgramView onNavigateToGenerate={() => handleTabChange('Generate Plan')} />
      ) : activeTab === 'Generate Plan' ? (
        <WorkoutPlanGenerator />
      ) : isLoading ? (
        <div className="space-y-6 text-left">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : isError ? (
        <ErrorState
          title="Error Loading Workouts"
          message="Failed to retrieve workouts from the library. Please check your connection and try again."
          onRetry={refetchWorkouts}
        />
      ) : (
        /* Main Grid Layout */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Library Section (8 of 12 columns on desktop) */}
          <div className="lg:col-span-8 space-y-6">
            <FeaturedWorkoutsSection workouts={workouts} />
            <WorkoutsTableList workouts={workouts} />
          </div>

          {/* Right Filter & Summary Panel (4 of 12 columns on desktop) */}
          <div className="lg:col-span-4">
            <WorkoutsRightPanel />
          </div>
        </div>
      )}
    </div>
  )
}


