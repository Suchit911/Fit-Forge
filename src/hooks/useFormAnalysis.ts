import { useQuery } from '@tanstack/react-query'
import { formAnalysisService } from '../services/formAnalysisService'

export function useFormAnalysis(exerciseId: string = 'ex_bench_press') {
  const {
    data: session,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['formAnalysisSession', exerciseId],
    queryFn: () => formAnalysisService.getFormAnalysisSession(exerciseId),
  })

  return {
    session,
    isLoading,
    isError,
    refetch,
  }
}
