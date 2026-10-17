import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { achievementsService } from '../services'

export function useAchievements() {
  const queryClient = useQueryClient()

  const dashboardQuery = useQuery({
    queryKey: ['achievementsDashboard'],
    queryFn: () => achievementsService.getDashboardData(),
  })

  const addAchievementMutation = useMutation({
    mutationFn: (data: { name: string; description: string; category: string }) =>
      achievementsService.addCustomAchievement(data.name, data.description, data.category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['achievementsDashboard'] })
    },
  })

  const clearNewMutation = useMutation({
    mutationFn: () => achievementsService.clearNewAchievements(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['achievementsDashboard'] })
    },
  })

  return {
    dashboardData: dashboardQuery.data,
    isLoading: dashboardQuery.isLoading,
    isError: dashboardQuery.isError,
    refetch: dashboardQuery.refetch,
    addAchievement: addAchievementMutation.mutateAsync,
    isAdding: addAchievementMutation.isPending,
    clearNew: clearNewMutation.mutateAsync,
  }
}
