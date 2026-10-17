import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { profileService } from '../services'

export function useProfile() {
  const queryClient = useQueryClient()

  const profileQuery = useQuery({
    queryKey: ['profileData'],
    queryFn: () => profileService.getProfileData(),
  })

  const updateProfileMutation = useMutation({
    mutationFn: (data: { name: string; age: number; heightCm: number; weightKg: number; fitnessGoal: string; activityLevel: string }) =>
      profileService.updateProfileInfo(data.name, data.age, data.heightCm, data.weightKg, data.fitnessGoal, data.activityLevel),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profileData'] })
    },
  })

  const updateGoalMutation = useMutation({
    mutationFn: (data: { primaryGoal: string; targetWeightKg: number; weeklyTarget: string; targetDate: string }) =>
      profileService.updateGoal(data.primaryGoal, data.targetWeightKg, data.weeklyTarget, data.targetDate),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profileData'] })
    },
  })

  return {
    profile: profileQuery.data,
    isLoading: profileQuery.isLoading,
    isError: profileQuery.isError,
    refetch: profileQuery.refetch,
    updateProfile: updateProfileMutation.mutateAsync,
    updateGoal: updateGoalMutation.mutateAsync,
  }
}
