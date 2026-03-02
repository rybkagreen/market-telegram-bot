import { apiClient } from './client'

export interface SummaryData {
  credits: number
  plan: 'free' | 'starter' | 'pro' | 'business'
  plan_expires_at: string | null
  ai_generations_used: number
  ai_included: number
  total_sent: number
  total_failed: number
  success_rate: number
  campaigns_count: number
  campaigns_active: number
}

export interface ActivityPoint {
  date: string
  sent: number
  failed: number
}

export interface ActivityData {
  points: ActivityPoint[]
  total_sent: number
  period_days: number
}

export const analyticsApi = {
  summary: (): Promise<SummaryData> =>
    apiClient.get('/analytics/summary').then(r => r.data),

  activity: (days = 7): Promise<ActivityData> =>
    apiClient.get(`/analytics/activity?days=${days}`).then(r => r.data),

  topChats: (limit = 10): Promise<TopChatsData> =>
    apiClient.get(`/analytics/top-chats?limit=${limit}`).then(r => r.data),

  topics: (): Promise<TopicsData> =>
    apiClient.get('/analytics/topics').then(r => r.data),

  campaignAiInsights: (campaignId: number): Promise<AIInsights> =>
    apiClient.get(`/analytics/campaigns/${campaignId}/ai-insights`).then(r => r.data),
}

export interface TopicItem {
  topic: string
  count: number
  percentage: number
}

export interface TopicsData {
  topics: TopicItem[]
}

export interface TopChatItem {
  username: string | null
  title: string
  member_count: number
  sent_count: number
  success_rate: number
}

export interface TopChatsData {
  chats: TopChatItem[]
}

export interface AIInsights {
  campaign_id: number
  plan: string
  insights: string[]
  recommendations: string[]
  performance_grade: 'A' | 'B' | 'C' | 'D' | 'N/A'
  forecast: string | null
  ab_test_suggestion: string | null
  generated_at: string
}
