import React, { useState } from 'react'
import { useHelpCenter } from '../../hooks'
import { HelpCenterHeader } from '../../components/help-center/HelpCenterHeader'
import { HelpCenterSearch } from '../../components/help-center/HelpCenterSearch'
import { PopularTopicsSection } from '../../components/help-center/PopularTopicsSection'
import { QuickHelpSection } from '../../components/help-center/QuickHelpSection'
import { FAQSection } from '../../components/help-center/FAQSection'
import { AskAICoachCard } from '../../components/help-center/AskAICoachCard'
import { ContactSupportCard } from '../../components/help-center/ContactSupportCard'
import { SystemStatusCard } from '../../components/help-center/SystemStatusCard'
import { HelpArticleModal } from '../../components/help-center/HelpArticleModal'
import { SupportModal } from '../../components/help-center/SupportModal'
import { Skeleton, ErrorState } from '../../components/ui'
import type { HelpTopicItem, QuickHelpGuideItem, ContactOptionRow } from '../../types'

export const HelpCenterPage: React.FC = () => {
  const { helpData, isLoading, isError, refetch, searchQuery, setSearchQuery } = useHelpCenter()

  const [activeArticle, setActiveArticle] = useState<{
    title: string
    description: string
    readTime?: string
  } | null>(null)

  const [supportModalConfig, setSupportModalConfig] = useState<{
    isOpen: boolean
    title: string
    subtitle?: string
  }>({
    isOpen: false,
    title: '',
  })

  if (isLoading) {
    return (
      <div className="space-y-6 text-left">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (isError || !helpData) {
    return (
      <ErrorState
        title="Help Center Data Unavailable"
        message="Could not load help center knowledge base. Please try again."
        onRetry={refetch}
      />
    )
  }

  const handleTopicClick = (topic: HelpTopicItem) => {
    setActiveArticle({
      title: `${topic.title} Guide & Documentation`,
      description: `Comprehensive overview and step-by-step instructions for ${topic.title}. Learn how to configure targets, optimize tracking, and utilize AI assistance.`,
      readTime: '5 min read',
    })
  }

  const handleGuideClick = (guide: QuickHelpGuideItem) => {
    setActiveArticle({
      title: guide.title,
      description: guide.description,
      readTime: guide.readTime,
    })
  }

  const handleContactOptionClick = (opt: ContactOptionRow) => {
    setSupportModalConfig({
      isOpen: true,
      title: opt.title,
      subtitle: opt.description,
    })
  }

  return (
    <div className="space-y-6 text-left pb-12">
      {/* Top Header */}
      <HelpCenterHeader />

      {/* Global Search Bar */}
      <HelpCenterSearch value={searchQuery} onChange={setSearchQuery} />

      {/* Main Two-Column Layout (8 cols & 4 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left / Center Column (8 of 12 cols) */}
        <div className="lg:col-span-8 space-y-6">
          <PopularTopicsSection
            topics={helpData.topics}
            onTopicClick={handleTopicClick}
            onViewAllClick={() =>
              setActiveArticle({
                title: 'All Topics Catalog',
                description: 'Browse the entire index of 100+ fitness, nutrition, AI, and tracking articles.',
              })
            }
          />

          <QuickHelpSection
            guides={helpData.guides}
            onGuideClick={handleGuideClick}
            onViewAllClick={() =>
              setActiveArticle({
                title: 'All Video & Quick Help Guides',
                description: 'Full directory of walkthroughs and quick-start tutorials.',
              })
            }
          />

          <FAQSection
            faqs={helpData.faqs}
            onViewAllClick={() =>
              setActiveArticle({
                title: 'Full Knowledge Base FAQ',
                description: 'Answers to over 50 frequently asked questions regarding AI FITNESS features.',
              })
            }
            onContactSupportClick={() =>
              setSupportModalConfig({
                isOpen: true,
                title: 'Contact Support',
                subtitle: 'Send a message to our customer support engineering team.',
              })
            }
          />
        </div>

        {/* Right Column (4 of 12 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <AskAICoachCard />

          <ContactSupportCard
            options={helpData.contactOptions}
            onOptionClick={handleContactOptionClick}
            onViewAllClick={() =>
              setSupportModalConfig({
                isOpen: true,
                title: 'Support Channels',
                subtitle: 'Choose your preferred channel: Chat, Email, or Ticket.',
              })
            }
          />

          <SystemStatusCard
            statusRows={helpData.systemStatus}
            onViewDetailedStatusClick={() =>
              setSupportModalConfig({
                isOpen: true,
                title: 'System Status Dashboard',
                subtitle: 'Real-time telemetry and operational status for AI FITNESS microservices.',
              })
            }
          />
        </div>
      </div>

      {/* Article Detail Modal */}
      <HelpArticleModal
        isOpen={Boolean(activeArticle)}
        onClose={() => setActiveArticle(null)}
        title={activeArticle?.title || 'Help Article'}
        description={activeArticle?.description || ''}
        readTime={activeArticle?.readTime}
      />

      {/* Support Action Modal */}
      <SupportModal
        isOpen={supportModalConfig.isOpen}
        onClose={() => setSupportModalConfig({ ...supportModalConfig, isOpen: false })}
        title={supportModalConfig.title}
        subtitle={supportModalConfig.subtitle}
      />
    </div>
  )
}
