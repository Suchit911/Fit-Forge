import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useWorkoutDetail } from '../../hooks'
import { WorkoutDetailsHeader } from '../../components/workout/WorkoutDetailsHeader'
import { WorkoutHeroCard } from '../../components/workout/WorkoutHeroCard'
import { WorkoutTabsNav } from '../../components/workout/WorkoutTabsNav'
import { ExercisePlanList } from '../../components/workout/ExercisePlanList'
import { WorkoutSummaryPanel } from '../../components/workout/WorkoutSummaryPanel'
import { EquipmentNeededPanel } from '../../components/workout/EquipmentNeededPanel'
import { WorkoutAICoachTip } from '../../components/workout/WorkoutAICoachTip'
import { TodaysFocusPanel } from '../../components/workout/TodaysFocusPanel'
import { RecommendedForYouPanel } from '../../components/workout/RecommendedForYouPanel'
import { Skeleton, ErrorState, EmptyState } from '../../components/ui'

export const WorkoutDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const workoutId = id || ''
  const { workout, isLoading, isError, refetch } = useWorkoutDetail(workoutId)

  if (!workoutId) {
    return (
      <EmptyState
        title="Workout Not Found"
        description="No workout ID was provided."
        actionLabel="Back to Workouts"
        onAction={() => navigate('/workouts')}
      />
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="Error Loading Workout"
        message="Could not retrieve workout details. Please check your connection and try again."
        onRetry={refetch}
      />
    )
  }

  if (!workout) {
    return (
      <EmptyState
        title="Workout Not Found"
        description="The requested workout plan does not exist in the library."
        actionLabel="Back to Workouts"
        onAction={() => navigate('/workouts')}
      />
    )
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Bar Header with Breadcrumbs */}
      <WorkoutDetailsHeader title={workout.title} />

      {/* Main Workout Hero Banner */}
      <WorkoutHeroCard
        workoutId={workoutId}
        title={workout.title}
        subtitle={workout.description}
        environment={workout.targetEnvironment}
        exerciseCount={workout.exercises?.length || 0}
        duration={workout.estimatedDurationMinutes || 45}
        difficulty={workout.difficulty}
        description={workout.description || 'No description available for this workout.'}
        image="/assets/dashboard_push_lifter.jpg"
      />

      {/* Workout Tabs Navigation */}
      <WorkoutTabsNav />

      {/* Main Content Grid: Exercise Plan on Left, Summary Panels on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Primary Exercise Plan Column (8 of 12 columns on desktop) */}
        <div className="lg:col-span-8">
          <ExercisePlanList exercises={workout.exercises} />
        </div>


        {/* Right Supporting Panels Column (4 of 12 columns on desktop) */}
        <div className="lg:col-span-4 space-y-6">
          <WorkoutSummaryPanel />
          <EquipmentNeededPanel />
          <WorkoutAICoachTip />
          <TodaysFocusPanel />
          <RecommendedForYouPanel />
        </div>

      </div>
    </div>
  )
}
