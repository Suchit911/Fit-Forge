import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useExerciseDetail } from '../../hooks'
import { ExerciseDetailsHeader } from '../../components/exercise/ExerciseDetailsHeader'
import { ExerciseHeroCard } from '../../components/exercise/ExerciseHeroCard'
import { ExerciseTabsNav } from '../../components/exercise/ExerciseTabsNav'
import { HowToPerformCard } from '../../components/exercise/HowToPerformCard'
import { PrimaryMusclesCard } from '../../components/exercise/PrimaryMusclesCard'
import { AnimationGuideSection } from '../../components/exercise/AnimationGuideSection'
import { SetRepRecommendationsSection } from '../../components/exercise/SetRepRecommendationsSection'
import { ExerciseOverviewPanel } from '../../components/exercise/ExerciseOverviewPanel'
import { EquipmentNeededDetailPanel } from '../../components/exercise/EquipmentNeededDetailPanel'
import { SimilarExercisesPanel } from '../../components/exercise/SimilarExercisesPanel'
import { PersonalRecordsPanel } from '../../components/exercise/PersonalRecordsPanel'
import { ExerciseVideoModal } from '../../components/exercise/ExerciseVideoModal'
import { Skeleton, ErrorState, EmptyState } from '../../components/ui'

export const ExerciseDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const exerciseId = id || ''
  const { exercise, isLoading, isError, refetch } = useExerciseDetail(exerciseId)

  const [activeTab, setActiveTab] = useState('Overview')
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false)

  if (!exerciseId) {
    return (
      <EmptyState
        title="Exercise Not Found"
        description="No exercise ID was provided."
        actionLabel="Back to Exercises"
        onAction={() => navigate('/exercises')}
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
        title="Error Loading Exercise"
        message="Could not retrieve exercise details. Please check your connection and try again."
        onRetry={refetch}
      />
    )
  }

  if (!exercise) {
    return (
      <EmptyState
        title="Exercise Not Found"
        description="The requested exercise does not exist in the library."
        actionLabel="Back to Exercises"
        onAction={() => navigate('/exercises')}
      />
    )
  }

  const primaryMuscle = exercise.primaryMuscles[0] || 'full_body'
  const secondaryMuscles = exercise.secondaryMuscles.join(', ') || 'None'

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header & Breadcrumb */}
      <ExerciseDetailsHeader category={primaryMuscle} title={exercise.name} />

      {/* Hero Overview Card */}
      <ExerciseHeroCard
        title={exercise.name}
        rating={4.9}
        reviewCount={1248}
        description={exercise.description || 'No description available for this exercise.'}
        muscles={`${primaryMuscle.charAt(0).toUpperCase() + primaryMuscle.slice(1)}, ${secondaryMuscles}`}
        equipment={exercise.equipment.map((eq) => eq.replace(/_/g, ' ')).join(', ') || 'Bodyweight'}
        difficulty={exercise.difficulty.charAt(0).toUpperCase() + exercise.difficulty.slice(1)}
        type={exercise.category.charAt(0).toUpperCase() + exercise.category.slice(1)}
        image="/assets/dashboard_push_lifter.jpg"
        onWatchVideoClick={() => setIsVideoModalOpen(true)}
      />

      {/* Exercise Tabs Navigation */}
      <ExerciseTabsNav activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Multi-Column Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Primary Column (8 of 12 columns on desktop) */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Row 1: How to Perform & Primary Muscles */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <HowToPerformCard instructions={exercise.instructions} />
            <PrimaryMusclesCard />
          </div>

          {/* Row 2: Animation Guide */}
          <AnimationGuideSection />

          {/* Row 3: Set & Rep Recommendations */}
          <SetRepRecommendationsSection />

        </div>

        {/* Right Supporting Column (4 of 12 columns on desktop) */}
        <div className="lg:col-span-4 space-y-6">
          <ExerciseOverviewPanel />
          <EquipmentNeededDetailPanel equipment={exercise.equipment} />
          <SimilarExercisesPanel />
          <PersonalRecordsPanel />
        </div>

      </div>

      {/* Exercise Video Modal */}
      <ExerciseVideoModal
        isOpen={isVideoModalOpen}
        onClose={() => setIsVideoModalOpen(false)}
        exerciseName={exercise.name}
        image="/assets/dashboard_push_lifter.jpg"
      />
    </div>
  )
}
