import { useQuery } from '@tanstack/react-query'
import { adaptationService } from '../services/adaptationService'

export function useAdaptationDecisions(windowDays: number = 28) {
  const adaptationsQuery = useQuery({
    queryKey: ['adaptationDecisions', windowDays],
    queryFn: () => adaptationService.getAdaptations(windowDays),
  })

  return {
    adaptations: adaptationsQuery.data,
    decisions: adaptationsQuery.data?.primaryDecisions || [],
    splitProposal: adaptationsQuery.data?.futureSplitProposal,
    summaryMetrics: adaptationsQuery.data?.summaryMetrics,
    isLoading: adaptationsQuery.isLoading,
    isError: adaptationsQuery.isError,
    error: adaptationsQuery.error,
    refetch: adaptationsQuery.refetch,
  }
}
