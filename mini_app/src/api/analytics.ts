// ВАЖНО (RT-001): advertiser и owner — это РАЗНЫЕ endpoint-ы с РАЗНЫМИ данными!
// Никогда не перепутывать их местами.

import { api } from './client'
import type { AdvertiserAnalytics, OwnerAnalytics } from '@/lib/types'

export interface AnalyticsSummary {
  credits: number
  plan: string
  plan_expires_at: string | null
  ai_generations_used: number
  ai_included: number
  total_sent: number
  total_failed: number
  success_rate: number
  campaigns_count: number
  campaigns_active: number
}

export interface AnalyticsActivity {
  dates: string[]
  sent: number[]
  failed: number[]
}

export interface PublicStats {
  total_channels: number
  total_users: number
  total_campaigns: number
  avg_campaign_success_rate: number
}

export interface AiInsight {
  insight: string
  confidence: number
}

export interface AiInsightsResponse {
  campaign_id: number
  plan: string
  insights: string[]
  recommendations: string[]
  performance_grade: string
  forecast: string | null
  ab_test_suggestion: string | null
  generated_at: string
}

export interface TopChatItem {
  username: string | null
  title: string
  member_count: number
  sent_count: number
  success_rate: number
}

export interface TopChatsResponse {
  chats: TopChatItem[]
}

export interface TopicItem {
  topic: string
  count: number
  percentage: number
}

export interface TopicsResponse {
  topics: TopicItem[]
}

export interface ReputationHistoryItem {
  id: number
  user_id: number
  action: string
  delta: number
  score_before: number
  score_after: number
  role: string
  comment: string | null
  created_at: string
}

export interface ReputationHistory {
  items: ReputationHistoryItem[]
  total: number
  page: number
  pages: number
}

export function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  return api.get('analytics/summary').json<AnalyticsSummary>()
}

export function getAnalyticsActivity(days: number = 7): Promise<AnalyticsActivity> {
  return api.get('analytics/activity', { searchParams: { days } }).json<AnalyticsActivity>()
}

export function getPublicStats(): Promise<PublicStats> {
  return api.get('analytics/stats/public').json<PublicStats>()
}

export function getCampaignAiInsights(campaignId: number): Promise<AiInsightsResponse> {
  return api.get(`analytics/campaigns/${campaignId}/ai-insights`).json<AiInsightsResponse>()
}

export function getTopChats(): Promise<TopChatsResponse> {
  return api.get('analytics/top-chats').json<TopChatsResponse>()
}

export function getAnalyticsTopics(): Promise<TopicsResponse> {
  return api.get('analytics/topics').json<TopicsResponse>()
}

export function getAdvertiserAnalytics(): Promise<AdvertiserAnalytics> {
  return api.get('analytics/advertiser').json<AdvertiserAnalytics>()
}

export function getOwnerAnalytics(): Promise<OwnerAnalytics> {
  return api.get('analytics/owner').json<OwnerAnalytics>()
}
