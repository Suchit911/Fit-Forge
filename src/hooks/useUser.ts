import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { User as FirebaseUser } from 'firebase/auth'
import { auth } from '../lib/firebase'
import { userService } from '../services'
import type { UserProfile } from '../types'

// Module-level shared auth listener to prevent duplicate subscriptions and repeated /users/me calls
let currentCachedAuthUser: FirebaseUser | null = auth?.currentUser || null
let isAuthListenerInitialized = false
const authSubscribers = new Set<(user: FirebaseUser | null) => void>()

function ensureGlobalAuthSubscription() {
  if (isAuthListenerInitialized) return
  isAuthListenerInitialized = true
  userService.onAuthStateChange((user) => {
    currentCachedAuthUser = user
    authSubscribers.forEach((cb) => cb(user))
  })
}

export function useUser() {
  const queryClient = useQueryClient()
  const [authUser, setAuthUser] = useState<FirebaseUser | null>(() => currentCachedAuthUser || auth?.currentUser || null)
  const [isAuthLoading, setIsAuthLoading] = useState<boolean>(!currentCachedAuthUser && Boolean(auth))

  useEffect(() => {
    ensureGlobalAuthSubscription()
    if (auth?.currentUser && !authUser) {
      setAuthUser(auth.currentUser)
      setIsAuthLoading(false)
    }

    const handler = (user: FirebaseUser | null) => {
      setAuthUser(user)
      setIsAuthLoading(false)
    }
    authSubscribers.add(handler)
    return () => {
      authSubscribers.delete(handler)
    }
  }, [authUser])

  const userQuery = useQuery({
    queryKey: ['userProfile', authUser?.uid],
    queryFn: () => userService.getUserProfile(),
    enabled: Boolean(authUser?.uid),
    staleTime: 1000 * 60 * 5, // 5 minutes fresh
    refetchOnWindowFocus: false,
    retry: 1,
  })

  const updateProfileMutation = useMutation({
    mutationFn: (updates: Partial<UserProfile>) => userService.updateUserProfile(updates),
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(['userProfile', authUser?.uid], updatedProfile)
      queryClient.invalidateQueries({ queryKey: ['profileData'] })
    },
  })

  const login = async (email: string, pass: string) => {
    const user = await userService.login(email, pass)
    setAuthUser(user)
    await queryClient.invalidateQueries({ queryKey: ['userProfile'] })
    return user
  }

  const register = async (email: string, pass: string, name?: string) => {
    const profile = await userService.register(email, pass, name)
    if (auth?.currentUser) {
      setAuthUser(auth.currentUser)
    }
    await queryClient.invalidateQueries({ queryKey: ['userProfile'] })
    return profile
  }

  const logout = async () => {
    await userService.logout()
    setAuthUser(null)
    queryClient.clear()
  }

  return {
    user: userQuery.data,
    authUser,
    isAuthenticated: Boolean(authUser),
    isAuthLoading,
    isLoading: isAuthLoading || (Boolean(authUser?.uid) && userQuery.isLoading),
    isError: userQuery.isError,
    error: userQuery.error,
    refetch: userQuery.refetch,
    updateProfile: updateProfileMutation.mutateAsync,
    isUpdating: updateProfileMutation.isPending,
    login,
    register,
    logout,
  }
}
