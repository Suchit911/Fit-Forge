import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { nutritionService } from '../services/nutritionService'

export function useNutrition(date?: string) {
  const queryClient = useQueryClient()

  const nutritionQuery = useQuery({
    queryKey: ['dailyNutrition', date],
    queryFn: () => nutritionService.getDailyNutrition(date),
  })

  const logMealMutation = useMutation({
    mutationFn: (mealData: {
      mealId: string
      foodName: string
      calories: number
      protein: number
      carbs: number
      fat: number
      fiber?: number
      sugar?: number
      sodium?: number
      servingSizeGrams?: number
      date?: string
    }) =>
      nutritionService.logMealItem(
        mealData.mealId,
        mealData.foodName,
        mealData.calories,
        mealData.protein,
        mealData.carbs,
        mealData.fat,
        {
          fiber: mealData.fiber,
          sugar: mealData.sugar,
          sodium: mealData.sodium,
          servingSizeGrams: mealData.servingSizeGrams,
          date: mealData.date || date,
        }
      ),
    onSuccess: (updatedNutrition) => {
      queryClient.setQueryData(['dailyNutrition', date], updatedNutrition)
      queryClient.invalidateQueries({ queryKey: ['dailyNutrition', date] })
    },
  })

  const logWaterMutation = useMutation({
    mutationFn: (amountLiters: number = 0.3) => nutritionService.logWater(amountLiters, date),
    onSuccess: (updatedNutrition) => {
      queryClient.setQueryData(['dailyNutrition', date], updatedNutrition)
      queryClient.invalidateQueries({ queryKey: ['dailyNutrition', date] })
    },
  })

  const deleteFoodMutation = useMutation({
    mutationFn: ({ mealId, foodId }: { mealId: string; foodId: string }) =>
      nutritionService.deleteMealFood(mealId, foodId, date),
    onSuccess: (updatedNutrition) => {
      queryClient.setQueryData(['dailyNutrition', date], updatedNutrition)
      queryClient.invalidateQueries({ queryKey: ['dailyNutrition', date] })
    },
  })

  return {
    nutrition: nutritionQuery.data,
    isLoading: nutritionQuery.isLoading,
    isError: nutritionQuery.isError,
    error: nutritionQuery.error,
    refetch: nutritionQuery.refetch,
    logMeal: logMealMutation.mutateAsync,
    isLogging: logMealMutation.isPending,
    logMealError: logMealMutation.error,
    logWater: logWaterMutation.mutateAsync,
    isLoggingWater: logWaterMutation.isPending,
    deleteFood: deleteFoodMutation.mutateAsync,
    isDeletingFood: deleteFoodMutation.isPending,
  }
}
