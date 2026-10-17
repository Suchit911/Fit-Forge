import React, { useState } from 'react'
import { useNutrition } from '../../hooks'
import { NutritionHeader } from '../../components/nutrition/NutritionHeader'
import { NutritionTabs } from '../../components/nutrition/NutritionTabs'
import { MacroSummaryStrip } from '../../components/nutrition/MacroSummaryStrip'
import { TodaysMeals } from '../../components/nutrition/TodaysMeals'
import { NutrientTargetsCard } from '../../components/nutrition/NutrientTargetsCard'
import { CalorieFlowCard } from '../../components/nutrition/CalorieFlowCard'
import { MacroBreakdownCard } from '../../components/nutrition/MacroBreakdownCard'
import { WaterIntakeCard } from '../../components/nutrition/WaterIntakeCard'
import { NutritionInsightsCard } from '../../components/nutrition/NutritionInsightsCard'
import { QuickActionsCard } from '../../components/nutrition/QuickActionsCard'
import { WeeklyNutritionSummaryCard } from '../../components/nutrition/WeeklyNutritionSummaryCard'
import { MealLoggerModal } from '../../components/nutrition/MealLoggerModal'
import { Skeleton, ErrorState } from '../../components/ui'
import { useToast } from '../../components/ui/Toast'
import { getTodayDateString, formatDisplayDate, shiftDateString } from '../../services/nutritionService'

export const NutritionPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(getTodayDateString())
  const [activeTab, setActiveTab] = useState('Overview')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const { showToast } = useToast()

  const { nutrition, isLoading, isError, refetch, logWater, deleteFood } = useNutrition(selectedDate)

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

  if (isError || !nutrition) {
    return (
      <ErrorState
        title="Nutrition Data Unavailable"
        message="Could not load daily nutrition summary. Please try again."
        onRetry={refetch}
      />
    )
  }

  const handleAddWater = async () => {
    try {
      await logWater(0.3)
      showToast('Logged 0.3L water', 'success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to log water'
      showToast(msg, 'error')
    }
  }

  const handleDeleteFood = async (mealId: string, foodId: string) => {
    try {
      await deleteFood({ mealId, foodId })
      showToast('Food item removed', 'success')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete food item'
      showToast(msg, 'error')
    }
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <NutritionHeader onMealPlannerClick={() => setIsModalOpen(true)} />

      {/* Navigation Tabs & Date Selector */}
      <NutritionTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        currentDate={formatDisplayDate(selectedDate)}
        onPrevDate={() => setSelectedDate((prev) => shiftDateString(prev, -1))}
        onNextDate={() => setSelectedDate((prev) => shiftDateString(prev, 1))}
      />

      {/* Macronutrient Summary Strip */}
      <MacroSummaryStrip
        consumedCalories={nutrition.consumedCalories}
        targetCalories={nutrition.targetCalories}
        consumedProtein={nutrition.consumedProteinGrams}
        targetProtein={nutrition.targetProteinGrams}
        consumedCarbs={nutrition.consumedCarbsGrams}
        targetCarbs={nutrition.targetCarbsGrams}
        consumedFat={nutrition.consumedFatGrams}
        targetFat={nutrition.targetFatGrams}
      />

      {/* Main Multi-Column Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column (8 of 12 columns on desktop) */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Sub-Grid: Today's Meals & Nutrient Targets/Calorie Flow */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <TodaysMeals meals={nutrition.meals} onDeleteFood={handleDeleteFood} />

            <div className="space-y-6">
              <NutrientTargetsCard
                targets={nutrition.nutrientTargets}
                onEditGoalsClick={() => setIsModalOpen(true)}
              />
              <CalorieFlowCard flow={nutrition.calorieFlow} />
            </div>
          </div>

          {/* Weekly Nutrition Summary Card */}
          <WeeklyNutritionSummaryCard days={nutrition.weeklySummary} />

        </div>

        {/* Right Column (4 of 12 columns on desktop) */}
        <div className="lg:col-span-4 space-y-6">
          <MacroBreakdownCard
            consumedCalories={nutrition.consumedCalories}
            proteinGrams={nutrition.consumedProteinGrams}
            carbsGrams={nutrition.consumedCarbsGrams}
            fatGrams={nutrition.consumedFatGrams}
          />
          <WaterIntakeCard
            waterLiters={nutrition.waterIntakeLiters ?? 0.0}
            targetLiters={nutrition.waterTargetLiters || 3.0}
            onAddWater={handleAddWater}
          />
          <NutritionInsightsCard insights={nutrition.insights} />
          <QuickActionsCard
            onLogMealClick={() => setIsModalOpen(true)}
            onScanFoodClick={() => showToast('Camera / food scanning is a placeholder and coming in a future phase.', 'info')}
            onMealPlannerClick={() => showToast('AI Meal Planner is coming in a future phase.', 'info')}
            onFoodDiaryClick={() => setIsModalOpen(true)}
          />
        </div>

      </div>

      {/* Meal Logger Modal */}
      <MealLoggerModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={refetch}
        date={selectedDate}
      />
    </div>
  )
}
