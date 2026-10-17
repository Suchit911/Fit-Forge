import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { progressService } from '../services'

export function useProgress(period: string = '30d') {
  const queryClient = useQueryClient()

  const progressQuery = useQuery({
    queryKey: ['progressSummary', period],
    queryFn: () => progressService.getProgressSummary(period),
  })

  const logWeightMutation = useMutation({
    mutationFn: ({ weightKg, date }: { weightKg: number; date?: string }) => progressService.logWeight(weightKg, date),
    onSuccess: (updatedProgress) => {
      queryClient.setQueryData(['progressSummary'], updatedProgress)
    },
  })

  return {
    progress: progressQuery.data,
    isLoading: progressQuery.isLoading,
    isError: progressQuery.isError,
    logWeight: logWeightMutation.mutateAsync,
    isLogging: logWeightMutation.isPending,
    refetch: progressQuery.refetch,
  }
}
