import { useQuery } from '@tanstack/react-query'
import { personalizationService } from '../services/personalizationService'

export function usePersonalizationSignals(windowDays: number = 28) {
  const signalsQuery = useQuery({
    queryKey: ['personalizationSignals', windowDays],
    queryFn: () => personalizationService.getPersonalizationSignals(windowDays),
  })

  return {
    signals: signalsQuery.data,
    isLoading: signalsQuery.isLoading,
    isError: signalsQuery.isError,
    error: signalsQuery.error,
    refetch: signalsQuery.refetch,
  }
}

export function useExercisePerformanceSignal(exerciseId: string) {
  const exerciseQuery = useQuery({
    queryKey: ['exercisePerformanceSignal', exerciseId],
    queryFn: () => personalizationService.getExercisePerformanceSignal(exerciseId),
    enabled: !!exerciseId,
  })

  return {
    performance: exerciseQuery.data,
    isLoading: exerciseQuery.isLoading,
    isError: exerciseQuery.isError,
    error: exerciseQuery.error,
    refetch: exerciseQuery.refetch,
  }
}
