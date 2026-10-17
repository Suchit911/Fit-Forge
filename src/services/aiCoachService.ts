import type {
  AIChatConversation,
  AIChatMessage,
  AICoachDashboardData,
  AICoachWeeklyMetric,
  SuggestedQuestionItem,
  AIRecommendation,
  CoachConversation,
  ConversationSummary,
  CoachMessage,
  CoachMessageResponse,
  UserProfile,
} from '../types'
import { getIdToken } from '../lib/firebase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

/**
 * Derives a human-friendly display time for a message from its ISO timestamp.
 */
export function formatMessageTimestamp(createdAtIso?: string): string {
  if (!createdAtIso) return 'Just now'
  try {
    const d = new Date(createdAtIso)
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  } catch {
    return 'Just now'
  }
}

/**
 * Derives local browser calendar date grouping and display time from authoritative createdAt/updatedAt ISO string.
 */
export function deriveConversationDisplay(conv: ConversationSummary | CoachConversation): {
  dateGroup: string
  timestamp: string
} {
  if (conv.dateGroup && conv.timestamp) {
    return { dateGroup: conv.dateGroup, timestamp: conv.timestamp }
  }

  const iso = conv.updatedAt || conv.createdAt
  if (!iso) {
    return { dateGroup: 'TODAY', timestamp: 'Recently' }
  }

  try {
    const itemDate = new Date(iso)
    const now = new Date()

    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const startOfYesterday = startOfToday - 86400000

    const itemTime = itemDate.getTime()
    const timeStr = itemDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

    if (itemTime >= startOfToday) {
      return { dateGroup: 'TODAY', timestamp: timeStr }
    } else if (itemTime >= startOfYesterday) {
      return { dateGroup: 'YESTERDAY', timestamp: `Yesterday` }
    } else {
      const dateStr = itemDate.toLocaleDateString([], { month: 'short', day: 'numeric' }).toUpperCase()
      return { dateGroup: dateStr, timestamp: timeStr }
    }
  } catch {
    return { dateGroup: 'RECENT', timestamp: 'Recently' }
  }
}

function mapConversation(raw: ConversationSummary | CoachConversation): AIChatConversation {
  const { dateGroup, timestamp } = deriveConversationDisplay(raw)
  return {
    id: raw.id,
    title: raw.title,
    previewText: raw.previewText || '',
    dateGroup,
    timestamp,
  }
}

function mapMessage(raw: CoachMessage): AIChatMessage {
  return {
    id: raw.id,
    sender: raw.sender,
    text: raw.text,
    timestamp: formatMessageTimestamp(raw.createdAt),
  }
}

// =============================================================================
// PRESENTATION METRICS (FOR SUPPORTING CARDS)
// =============================================================================

export function deriveCoachWeeklyMetrics(user?: UserProfile | null): AICoachWeeklyMetric[] {
  const totalWorkouts = user?.totalWorkouts || 0
  const workoutTarget = user?.workoutFrequencyDaysPerWeek || 4
  const workoutPct = workoutTarget > 0 ? Math.min(100, Math.round((totalWorkouts / workoutTarget) * 100)) : 0
  const targetCalories = user?.targetCalories || 0

  return [
    { title: 'Workouts', current: totalWorkouts, target: workoutTarget, unit: '', pct: workoutPct, color: '#10b981' },
    { title: 'Calories', current: 0, target: targetCalories, unit: '', pct: 0, color: '#f97316' },
    { title: 'Volume', current: 0, target: 10000, unit: 'kg', pct: 0, color: '#3b82f6' },
    { title: 'Sleep', current: 0, target: 8, unit: 'hrs', pct: 0, color: '#a855f7' },
  ]
}

export const presentationWeeklyMetrics: AICoachWeeklyMetric[] = deriveCoachWeeklyMetrics(null)

export const presentationInsights: AIRecommendation[] = [
  {
    type: 'workout_adaptation',
    title: 'Solid Consistency',
    description: 'You are on track with progressive overload this week.',
  },
  {
    type: 'form_tip',
    title: 'Scapular Retraction',
    description: 'Remember to keep shoulder blades retracted during bench press.',
  },
  {
    type: 'nutrition',
    title: 'Protein Target',
    description: 'Aim for 1.6-2.2g of protein per kg to optimize recovery.',
  },
]

export const presentationSuggestedQuestions: SuggestedQuestionItem[] = [
  { id: 'q1', question: 'Generate a 4-day workout plan for muscle gain', iconName: 'dumbbell', color: '#10b981' },
  { id: 'q2', question: 'What should I eat to build muscle faster?', iconName: 'utensils', color: '#3b82f6' },
  { id: 'q3', question: 'How can I improve my sleep and recovery?', iconName: 'heart', color: '#a855f7' },
  { id: 'q4', question: 'My lower back feels tight after deadlifts. Tips?', iconName: 'activity', color: '#f59e0b' },
  { id: 'q5', question: 'Which supplements are best for strength and power?', iconName: 'file-text', color: '#06b6d4' },
]

export const presentationSuggestedPrompts: string[] = [
  'Show me an optimal push day split',
  'How to improve bench press form?',
  'What are good pre-workout carbs?',
]

// =============================================================================
// AI COACH SERVICE
// =============================================================================

export const aiCoachService = {
  /**
   * Lists all conversations for the authenticated user from FastAPI.
   */
  async listConversations(limit = 20): Promise<AIChatConversation[]> {
    const token = await getIdToken()
    if (!token) {
      return []
    }

    const res = await fetch(`${API_BASE_URL}/coach/conversations?limit=${limit}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })

    if (!res.ok) {
      if (res.status === 401) {
        throw new Error('Authentication expired. Please sign in again.')
      }
      throw new Error(`Failed to load conversations (status ${res.status})`)
    }

    const rawList = (await res.json()) as ConversationSummary[]
    return rawList.map(mapConversation)
  },

  /**
   * Explicitly creates a new conversation thread on the backend.
   */
  async createConversation(title?: string, initialMessage?: string): Promise<AIChatConversation> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in.')
    }

    const payload: Record<string, string> = {}
    if (title) payload.title = title
    if (initialMessage) payload.initialMessage = initialMessage

    const res = await fetch(`${API_BASE_URL}/coach/conversations`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to create conversation')
    }

    const raw = (await res.json()) as CoachConversation
    return mapConversation(raw)
  },

  /**
   * Retrieves message history for a conversation from FastAPI.
   */
  async getMessages(conversationId: string, limit = 50): Promise<AIChatMessage[]> {
    const token = await getIdToken()
    if (!token) {
      return []
    }

    const res = await fetch(
      `${API_BASE_URL}/coach/conversations/${encodeURIComponent(conversationId)}/messages?limit=${limit}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    )

    if (!res.ok) {
      if (res.status === 404) {
        return []
      }
      if (res.status === 401) {
        throw new Error('Authentication expired. Please sign in again.')
      }
      throw new Error(`Failed to load messages (status ${res.status})`)
    }

    const rawList = (await res.json()) as CoachMessage[]
    return rawList.map(mapMessage)
  },

  /**
   * Deletes a conversation thread and its messages from FastAPI.
   */
  async deleteConversation(conversationId: string): Promise<{ success: boolean; id: string }> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in.')
    }

    const res = await fetch(
      `${API_BASE_URL}/coach/conversations/${encodeURIComponent(conversationId)}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    )

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to delete conversation')
    }

    return (await res.json()) as { success: boolean; id: string }
  },

  /**
   * Sends a user message to the AI Coach and returns the validated assistant reply.
   */
  async sendMessage(
    message: string,
    conversationId?: string
  ): Promise<{ conversationId: string; userMessage: AIChatMessage; assistantMessage: AIChatMessage }> {
    const token = await getIdToken()
    if (!token) {
      throw new Error('Authentication required. Please sign in to message your coach.')
    }

    const cleanMsg = message.trim()
    if (!cleanMsg) {
      throw new Error('Message cannot be empty.')
    }
    if (cleanMsg.length > 1000) {
      throw new Error('Message cannot exceed 1000 characters.')
    }

    const bodyPayload: Record<string, string> = { message: cleanMsg }
    if (conversationId && conversationId.trim()) {
      bodyPayload.conversation_id = conversationId.trim()
    }

    const res = await fetch(`${API_BASE_URL}/coach/chat`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(bodyPayload),
    })

    if (!res.ok) {
      const errJson = await res.json().catch(() => ({}))
      const detail = errJson.detail || ''

      if (res.status === 401) {
        throw new Error('Authentication expired. Please sign in again.')
      } else if (res.status === 404) {
        throw new Error('Conversation not found or has been deleted.')
      } else if (res.status === 422) {
        throw new Error(detail || 'Invalid message text provided.')
      } else if (res.status === 429) {
        throw new Error(
          detail || 'Message rate limit exceeded. Please wait a moment before sending another message.'
        )
      } else if (res.status === 503) {
        throw new Error(
          'AI Coach service is currently unconfigured on the backend (missing credentials).'
        )
      } else if (res.status === 504) {
        throw new Error('AI Coach response timed out after 12 seconds. Please try again.')
      } else if (res.status === 502) {
        throw new Error(
          detail || 'AI Coach provider is temporarily unavailable. Please try again shortly.'
        )
      } else {
        throw new Error(detail || `AI Coach error (status ${res.status}).`)
      }
    }

    const rawResponse = (await res.json()) as CoachMessageResponse
    return {
      conversationId: rawResponse.conversationId,
      userMessage: mapMessage(rawResponse.userMessage),
      assistantMessage: mapMessage(rawResponse.assistantMessage),
    }
  },

  /**
   * Supporting presentation data methods (preserving existing UI contracts)
   */
  getSuggestedPrompts(): string[] {
    return presentationSuggestedPrompts
  },

  getSuggestedQuestions(): SuggestedQuestionItem[] {
    return presentationSuggestedQuestions
  },

  getWeeklyMetrics(): AICoachWeeklyMetric[] {
    return presentationWeeklyMetrics
  },

  getInsights(): AIRecommendation[] {
    return presentationInsights
  },

  /**
   * Compatibility wrapper for initial dashboard data loading.
   */
  async getDashboardData(): Promise<AICoachDashboardData> {
    const conversations = await this.listConversations().catch(() => [])
    const activeId = conversations.length > 0 ? conversations[0].id : ''
    const messages = activeId ? await this.getMessages(activeId).catch(() => []) : []

    return {
      conversations,
      activeConversationId: activeId,
      messages,
      weeklyMetrics: this.getWeeklyMetrics(),
      insights: this.getInsights(),
      suggestedQuestions: this.getSuggestedQuestions(),
    }
  },

  async getChatHistory(): Promise<AIChatMessage[]> {
    const convs = await this.listConversations().catch(() => [])
    if (convs.length > 0) {
      return this.getMessages(convs[0].id).catch(() => [])
    }
    return []
  },
}
