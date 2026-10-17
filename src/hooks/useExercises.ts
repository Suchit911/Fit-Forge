import { useQuery } from '@tanstack/react-query'
import { exerciseService } from '../services'
import type { ExerciseFilterParams } from '../services'

export function useExercises(filters?: ExerciseFilterParams) {
  const exercisesQuery = useQuery({
    queryKey: ['exercises', filters],
    queryFn: () => exerciseService.getExercises(filters),
  })

  return {
    exercises: exercisesQuery.data || [],
    isLoading: exercisesQuery.isLoading,
    isError: exercisesQuery.isError,
    error: exercisesQuery.error,
    refetch: exercisesQuery.refetch,
  }
}

export function useExerciseDetail(id: string) {
  const exerciseQuery = useQuery({
    queryKey: ['exercise', id],
    queryFn: () => exerciseService.getExerciseById(id),
    enabled: !!id,
  })

  return {
    exercise: exerciseQuery.data,
    isLoading: exerciseQuery.isLoading,
    isError: exerciseQuery.isError,
    error: exerciseQuery.error,
    refetch: exerciseQuery.refetch,
  }
}

