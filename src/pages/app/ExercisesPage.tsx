import React, { useState } from 'react'
import { ExercisesHeader } from '../../components/exercise/ExercisesHeader'
import { ExerciseSearchBar } from '../../components/exercise/ExerciseSearchBar'
import { ExerciseTopStatsStrip } from '../../components/exercise/ExerciseTopStatsStrip'
import { PopularExercisesSection } from '../../components/exercise/PopularExercisesSection'
import { BrowseMuscleGroupSection } from '../../components/exercise/BrowseMuscleGroupSection'
import { NewlyAddedSection } from '../../components/exercise/NewlyAddedSection'
import { MuscleGroupsSidebarCard } from '../../components/exercise/MuscleGroupsSidebarCard'
import { EquipmentTypesSidebarCard } from '../../components/exercise/EquipmentTypesSidebarCard'
import { DifficultyDonutCard } from '../../components/exercise/DifficultyDonutCard'
import { ExerciseQuickActionsCard } from '../../components/exercise/ExerciseQuickActionsCard'
import { CreateCustomExerciseModal } from '../../components/exercise/CreateCustomExerciseModal'
import { useExercises } from '../../hooks'
import { Skeleton, ErrorState, EmptyState } from '../../components/ui'

export const ExercisesPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedMuscle, setSelectedMuscle] = useState('All')
  const [selectedEquipment, setSelectedEquipment] = useState('All')
  const [selectedDifficulty, setSelectedDifficulty] = useState('All')
  const [sortBy, setSortBy] = useState('popular')
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { exercises, isLoading, isError, refetch } = useExercises({
    muscle: selectedMuscle !== 'All' ? selectedMuscle : undefined,
    equipment: selectedEquipment !== 'All' ? selectedEquipment : undefined,
    difficulty: selectedDifficulty !== 'All' ? selectedDifficulty : undefined,
    searchQuery: searchQuery.trim() || undefined,
  })

  const handleResetFilters = () => {
    setSearchQuery('')
    setSelectedMuscle('All')
    setSelectedEquipment('All')
    setSelectedDifficulty('All')
  }

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="Error Loading Exercises"
        message="Failed to retrieve exercise library. Please check your connection and try again."
        onRetry={refetch}
      />
    )
  }

  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    selectedMuscle !== 'All' ||
    selectedEquipment !== 'All' ||
    selectedDifficulty !== 'All'

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Bar Header */}
      <ExercisesHeader onCreateCustomClick={() => setIsModalOpen(true)} />

      {/* Large Search Field & Filter Chips Bar */}
      <ExerciseSearchBar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedMuscle={selectedMuscle}
        onMuscleChange={setSelectedMuscle}
        selectedEquipment={selectedEquipment}
        onEquipmentChange={setSelectedEquipment}
        selectedDifficulty={selectedDifficulty}
        onDifficultyChange={setSelectedDifficulty}
        sortBy={sortBy}
        onSortChange={setSortBy}
      />

      {/* Top 4 Statistics Strip */}
      <ExerciseTopStatsStrip />

      {/* Main Multi-Column Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (8 of 12 columns on desktop) */}
        <div className="lg:col-span-8 space-y-6">
          {exercises.length === 0 ? (
            <EmptyState
              title="No Exercises Found"
              description={
                hasActiveFilters
                  ? 'No exercises match the selected filters. Try adjusting your search or clear filters.'
                  : 'There are currently no exercises in the library.'
              }
              actionLabel={hasActiveFilters ? 'Reset Filters' : undefined}
              onAction={hasActiveFilters ? handleResetFilters : undefined}
            />
          ) : (
            <>
              <PopularExercisesSection exercises={exercises} />
              <BrowseMuscleGroupSection onSelectMuscle={setSelectedMuscle} />
              <NewlyAddedSection exercises={exercises} />
            </>
          )}
        </div>

        {/* Right Column (4 of 12 columns on desktop) */}
        <div className="lg:col-span-4 space-y-6">
          <MuscleGroupsSidebarCard onSelectMuscle={setSelectedMuscle} />
          <EquipmentTypesSidebarCard onSelectEquipment={setSelectedEquipment} />
          <DifficultyDonutCard />
          <ExerciseQuickActionsCard onCreateCustomClick={() => setIsModalOpen(true)} />
        </div>

      </div>

      {/* Create Custom Exercise Modal */}
      <CreateCustomExerciseModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {}}
      />
    </div>
  )
}
