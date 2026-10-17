import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aiCoachService } from '../services'
import { useToast } from '../components/ui/Toast'
import type { AIChatMessage, AIChatConversation } from '../types'

export function useAICoach() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null)

  // 1. Fetch conversations list for authenticated user
  const conversationsQuery = useQuery({
    queryKey: ['coachConversations'],
    queryFn: () => aiCoachService.listConversations(),
    staleTime: 30000,
  })

  const conversations: AIChatConversation[] = conversationsQuery.data || []

  // Resolve active conversation ID:
  // If user explicitly picked one, use it. Otherwise, default to first available conversation.
  const activeConversationId: string | null =
    selectedConversationId !== null
      ? selectedConversationId
      : conversations.length > 0
      ? conversations[0].id
      : null

  // 2. Fetch messages for the active conversation
  const messagesQuery = useQuery({
    queryKey: ['coachMessages', activeConversationId],
    queryFn: () => (activeConversationId ? aiCoachService.getMessages(activeConversationId) : Promise.resolve([])),
    enabled: Boolean(activeConversationId),
    staleTime: 30000,
  })

  // 3. Create conversation mutation
  const createConversationMutation = useMutation({
    mutationFn: (title?: string) => aiCoachService.createConversation(title),
    onSuccess: (newConv) => {
      // Invalidate conversation list and switch to the newly created conversation
      queryClient.invalidateQueries({ queryKey: ['coachConversations'] })
      setSelectedConversationId(newConv.id)
      queryClient.setQueryData(['coachMessages', newConv.id], [])
    },
    onError: (err: any) => {
      showToast(err.message || 'Failed to create conversation', 'error')
    },
  })

  // 4. Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (text: string) => {
      return await aiCoachService.sendMessage(text, activeConversationId || undefined)
    },
    onSuccess: (res) => {
      // If thread was auto-created, update active conversation pointer
      if (!activeConversationId || activeConversationId !== res.conversationId) {
        setSelectedConversationId(res.conversationId)
      }

      // Optimistically update message cache for this thread
      queryClient.setQueryData<AIChatMessage[]>(
        ['coachMessages', res.conversationId],
        (prev = []) => [...prev, res.userMessage, res.assistantMessage]
      )

      // Invalidate conversations list so previewText, updatedAt, and messageCount update
      queryClient.invalidateQueries({ queryKey: ['coachConversations'] })
    },
    onError: (err: any) => {
      showToast(err.message || 'Failed to send message', 'error')
    },
  })

  // 5. Delete conversation mutation
  const deleteConversationMutation = useMutation({
    mutationFn: (conversationId: string) => aiCoachService.deleteConversation(conversationId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['coachConversations'] })
      queryClient.removeQueries({ queryKey: ['coachMessages', deletedId] })

      if (activeConversationId === deletedId) {
        const remaining = conversations.filter((c) => c.id !== deletedId)
        setSelectedConversationId(remaining.length > 0 ? remaining[0].id : null)
      }
      showToast('Conversation deleted', 'info')
    },
    onError: (err: any) => {
      showToast(err.message || 'Failed to delete conversation', 'error')
    },
  })

  const suggestedPrompts = aiCoachService.getSuggestedPrompts()

  return {
    conversations,
    activeConversationId,
    setActiveConversationId: (id: string | null) => setSelectedConversationId(id),
    messages: (messagesQuery.data || []) as AIChatMessage[],
    chatMessages: (messagesQuery.data || []) as AIChatMessage[],
    suggestedPrompts,
    isLoading: conversationsQuery.isLoading,
    isLoadingConversations: conversationsQuery.isLoading,
    isLoadingMessages: messagesQuery.isLoading && Boolean(activeConversationId),
    isSending: sendMessageMutation.isPending,
    isCreating: createConversationMutation.isPending,
    isDeleting: deleteConversationMutation.isPending,
    isError: conversationsQuery.isError,
    error: conversationsQuery.error,
    sendMessage: sendMessageMutation.mutateAsync,
    createConversation: createConversationMutation.mutateAsync,
    deleteConversation: deleteConversationMutation.mutateAsync,
    refetch: () => {
      conversationsQuery.refetch()
      if (activeConversationId) {
        messagesQuery.refetch()
      }
    },
  }
}
