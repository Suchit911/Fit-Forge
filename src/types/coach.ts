/**
 * Frontend types corresponding to Phase 8D FastAPI Coach contracts.
 */

export interface CoachConversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  previewText: string
  messageCount: number
  dateGroup?: string
  timestamp?: string
}

export interface ConversationSummary {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  previewText: string
  messageCount: number
  dateGroup?: string
  timestamp?: string
}

export interface CoachMessage {
  id: string
  conversationId: string
  sender: 'user' | 'assistant'
  text: string
  createdAt: string
  timestamp?: string
}

export interface CreateConversationRequest {
  title?: string
  initialMessage?: string
}

export interface SendCoachMessageRequest {
  conversation_id?: string
  conversationId?: string
  message: string
}

export interface CoachMessageResponse {
  conversationId: string
  userMessage: CoachMessage
  assistantMessage: CoachMessage
}
