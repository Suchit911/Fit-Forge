import type { HelpCenterDashboardData } from '../types'

export const mockHelpCenterDashboardData: HelpCenterDashboardData = {
  topics: [
    { id: 't1', title: 'Getting Started', articleCount: 12, iconName: 'rocket', color: '#10b981' },
    { id: 't2', title: 'Workouts', articleCount: 24, iconName: 'dumbbell', color: '#3b82f6' },
    { id: 't3', title: 'Exercise & Form', articleCount: 18, iconName: 'running', color: '#a855f7' },
    { id: 't4', title: 'Nutrition', articleCount: 22, iconName: 'utensils', color: '#f97316' },
    { id: 't5', title: 'AI Coach', articleCount: 16, iconName: 'bot', color: '#a855f7' },
    { id: 't6', title: 'Progress Tracking', articleCount: 14, iconName: 'chart', color: '#06b6d4' },
  ],
  guides: [
    {
      id: 'g1',
      title: 'How to start a workout',
      description: 'Step-by-step guide to begin your first workout',
      readTime: '5 min read',
      iconName: 'play',
      color: '#10b981',
    },
    {
      id: 'g2',
      title: 'How Form Analysis works',
      description: 'Understand AI-powered form correction',
      readTime: '4 min read',
      iconName: 'video',
      color: '#3b82f6',
    },
    {
      id: 'g3',
      title: 'How to create a custom workout',
      description: 'Build your personalized workout plan',
      readTime: '6 min read',
      iconName: 'plus',
      color: '#a855f7',
    },
    {
      id: 'g4',
      title: 'How to log meals',
      description: 'Track your nutrition the right way',
      readTime: '4 min read',
      iconName: 'utensils',
      color: '#f97316',
    },
    {
      id: 'g5',
      title: 'How AI Coach works',
      description: 'Personalized guidance powered by AI',
      readTime: '6 min read',
      iconName: 'bot',
      color: '#a855f7',
    },
    {
      id: 'g6',
      title: 'How to connect devices',
      description: 'Sync your wearables and apps',
      readTime: '3 min read',
      iconName: 'watch',
      color: '#06b6d4',
    },
  ],
  faqs: [
    {
      id: 'faq1',
      question: 'How do I create a custom workout plan?',
      answer: 'To create a custom workout plan, head over to the Workouts section and click "+ Create Workout". You can select exercises, define set/rep counts, and assign target RPE.',
    },
    {
      id: 'faq2',
      question: 'How accurate is the AI Form Analysis?',
      answer: 'AI Form Analysis uses computer vision pose estimation to measure joint angles and bar paths with up to 96% biomechanical accuracy during standard movements.',
    },
    {
      id: 'faq3',
      question: 'Can I sync AI FITNESS with my smartwatch?',
      answer: 'Yes! Go to Settings -> Connected Devices to pair Apple Watch, Fitbit, Google Fit, or Bluetooth HR monitors for continuous biometric tracking.',
    },
    {
      id: 'faq4',
      question: 'How do I update my fitness goals?',
      answer: 'Navigate to your Profile page and click "Edit Goal" on the Fitness Goals card to adjust your primary objective, target weight, or deadline.',
    },
    {
      id: 'faq5',
      question: 'Is my data secure with AI FITNESS?',
      answer: 'All biometric and workout data is encrypted in transit and at rest. You can manage data visibility and AI sharing preferences under Settings -> Privacy & Security.',
    },
  ],
  contactOptions: [
    { id: 'co1', title: 'Live Chat', description: 'Chat with our support team', statusAction: 'Online ●', iconName: 'message-square' },
    { id: 'co2', title: 'Email Support', description: 'support@aifitness.com', statusAction: '24h response >', iconName: 'mail' },
    { id: 'co3', title: 'Report a Problem', description: "Let us know what's not working", statusAction: "We'll fix it >", iconName: 'alert-triangle' },
  ],
  systemStatus: [
    { id: 'ss1', serviceName: 'AI Coach', status: 'Operational', iconName: 'bot' },
    { id: 'ss2', serviceName: 'Workout Tracking', status: 'Operational', iconName: 'dumbbell' },
    { id: 'ss3', serviceName: 'Nutrition', status: 'Operational', iconName: 'utensils' },
    { id: 'ss4', serviceName: 'Form Analysis', status: 'Operational', iconName: 'video' },
    { id: 'ss5', serviceName: 'Connected Devices', status: 'Operational', iconName: 'watch' },
  ],
}

export const helpCenterService = {
  async getHelpCenterData(): Promise<HelpCenterDashboardData> {
    return { ...mockHelpCenterDashboardData }
  },

  async searchHelp(query: string): Promise<HelpCenterDashboardData> {
    if (!query.trim()) return { ...mockHelpCenterDashboardData }
    const q = query.toLowerCase()
    return {
      ...mockHelpCenterDashboardData,
      faqs: mockHelpCenterDashboardData.faqs.filter(
        (f) => f.question.toLowerCase().includes(q) || f.answer.toLowerCase().includes(q)
      ),
      guides: mockHelpCenterDashboardData.guides.filter(
        (g) => g.title.toLowerCase().includes(q) || g.description.toLowerCase().includes(q)
      ),
    }
  },
}
