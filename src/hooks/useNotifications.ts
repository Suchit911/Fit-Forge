import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { notificationsService } from '../services'
import { useUser } from './useUser'

export function useNotifications() {
  const queryClient = useQueryClient()
  const { isAuthenticated } = useUser()
  const [activeFilter, setActiveFilter] = useState('All')

  // Full notifications dashboard data query
  const notificationsQuery = useQuery({
    queryKey: ['notificationsData'],
    queryFn: () => notificationsService.getNotificationsData(),
    enabled: !!isAuthenticated,
  })

  // Lightweight unread count polling query (30s interval while authenticated)
  const unreadCountQuery = useQuery({
    queryKey: ['notificationsUnreadCount'],
    queryFn: () => notificationsService.getUnreadCount(),
    enabled: !!isAuthenticated,
    refetchInterval: 30000,
  })

  const markAsReadMutation = useMutation({
    mutationFn: (id: string) => notificationsService.markAsRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationsData'] })
      queryClient.invalidateQueries({ queryKey: ['notificationsUnreadCount'] })
    },
  })

  const markAllAsReadMutation = useMutation({
    mutationFn: () => notificationsService.markAllAsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notificationsData'] })
      queryClient.invalidateQueries({ queryKey: ['notificationsUnreadCount'] })
    },
  })

  const notificationsData = notificationsQuery.data
  const unreadCount = unreadCountQuery.data ?? notificationsData?.unreadCount ?? 0

  const filteredNotifications = (notificationsData?.notifications || []).filter((n) => {
    if (activeFilter === 'All') return true
    if (activeFilter === 'Unread') return !n.read
    if (activeFilter === 'Workouts') return n.category === 'Workout'
    if (activeFilter === 'Achievements') return n.category === 'Achievement'
    if (activeFilter === 'AI Coach') return n.category === 'AI Coach' // Honest empty state in Phase 7
    return n.category === activeFilter
  })

  return {
    notificationsData,
    filteredNotifications,
    unreadCount,
    isLoading: notificationsQuery.isLoading,
    isError: notificationsQuery.isError,
    refetch: notificationsQuery.refetch,
    activeFilter,
    setActiveFilter,
    markAsRead: markAsReadMutation.mutateAsync,
    markAllAsRead: markAllAsReadMutation.mutateAsync,
  }
}
