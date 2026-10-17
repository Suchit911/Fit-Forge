import { useMutation } from '@tanstack/react-query'
import { workoutPlanService } from '../services/workoutPlanService'
import type { WorkoutPlanGenerateRequest, WorkoutPlanResponse } from '../types/workoutPlan'

export function useGenerateWorkoutPlan() {
  const mutation = useMutation<WorkoutPlanResponse, Error, WorkoutPlanGenerateRequest>({
    mutationFn: (request: WorkoutPlanGenerateRequest) => workoutPlanService.generateWorkoutPlan(request),
    retry: 0,
  })

  return {
    generatePlan: mutation.mutateAsync,
    isGenerating: mutation.isPending,
    data: mutation.data,
    error: mutation.error,
    reset: mutation.reset,
    isSuccess: mutation.isSuccess,
  }
}
