import React, { useState } from 'react'
import { useAICoach, useUser } from '../../hooks'
import { CoachHeader } from '../../components/coach/CoachHeader'
import { CoachTabs } from '../../components/coach/CoachTabs'
import { ChatHistoryPanel } from '../../components/coach/ChatHistoryPanel'
import { ChatConversationView } from '../../components/coach/ChatConversationView'
import { CoachStatusCard } from '../../components/coach/CoachStatusCard'
import { WeeklyProgressOverviewCard } from '../../components/coach/WeeklyProgressOverviewCard'
import { AICoachInsightsCard } from '../../components/coach/AICoachInsightsCard'
import { CoachQuickActionsCard } from '../../components/coach/CoachQuickActionsCard'
import { SuggestedQuestionsSection } from '../../components/coach/SuggestedQuestionsSection'
import { CoachSettingsModal } from '../../components/coach/CoachSettingsModal'
import { Skeleton, ErrorState } from '../../components/ui'
import {
  deriveCoachWeeklyMetrics,
  presentationInsights,
  presentationSuggestedQuestions,
} from '../../services/aiCoachService'

export const AICoachPage: React.FC = () => {
  const {
    conversations,
    activeConversationId,
    setActiveConversationId,
    messages,
    suggestedPrompts,
    isLoading,
    isSending,
    isError,
    sendMessage,
    createConversation,
    deleteConversation,
    refetch,
  } = useAICoach()
  const { user } = useUser()

  const [activeTab, setActiveTab] = useState('Chat')
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)

  const weeklyMetrics = deriveCoachWeeklyMetrics(user)

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="AI Coach Unavailable"
        message="Could not connect to AI Coach service. Please check your connection and try again."
        onRetry={refetch}
      />
    )
  }

  const activeConversation = conversations.find((c) => c.id === activeConversationId) || (conversations.length > 0 ? conversations[0] : null)
  const conversationTitle = activeConversation ? activeConversation.title : 'New AI Coach Conversation'

  const handleSendMessageText = async (text: string) => {
    try {
      await sendMessage(text)
    } catch {
      // Toast error is handled inside useAICoach mutation
    }
  }

  const handleNewChat = async () => {
    try {
      await createConversation('Workout Plan Advice')
    } catch {
      // Handled via toast
    }
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <CoachHeader onNewChatClick={handleNewChat} />

      {/* Sub-Header Navigation Tabs & Coach Settings Action */}
      <CoachTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onSettingsClick={() => setIsSettingsOpen(true)}
      />

      {/* Main Three-Column Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Chat History Panel (3 of 12 columns) */}
        <div className="lg:col-span-3">
          <ChatHistoryPanel
            conversations={conversations}
            activeId={activeConversationId || ''}
            onSelectConversation={setActiveConversationId}
            onNewChatClick={handleNewChat}
            onDeleteConversation={deleteConversation}
          />
        </div>

        {/* Center Column: Active Conversation Viewport (5 of 12 columns) */}
        <div className="lg:col-span-5">
          <ChatConversationView
            title={conversationTitle}
            messages={messages}
            suggestedPrompts={suggestedPrompts}
            onSendMessage={handleSendMessageText}
            onPromptClick={handleSendMessageText}
            onShareChat={() => alert('Chat link ready to share!')}
            isSending={isSending}
            onDeleteChat={activeConversationId ? () => deleteConversation(activeConversationId) : undefined}
          />
        </div>

        {/* Right Column: Coach Status & Supporting Panels (4 of 12 columns) */}
        <div className="lg:col-span-4 space-y-6">
          <CoachStatusCard />
          <WeeklyProgressOverviewCard metrics={weeklyMetrics} />
          <AICoachInsightsCard insights={presentationInsights} />
          <CoachQuickActionsCard onActionClick={(act) => alert(`Action: ${act}`)} />
        </div>

      </div>

      {/* Bottom Full-Width Section: Suggested Questions */}
      <SuggestedQuestionsSection
        questions={presentationSuggestedQuestions}
        onQuestionClick={handleSendMessageText}
      />

      {/* Coach Settings Modal */}
      <CoachSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  )
}
