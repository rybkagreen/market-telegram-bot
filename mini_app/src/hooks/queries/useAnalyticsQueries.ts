// ВАЖНО (RT-001): advertiser и owner — это РАЗНЫЕ endpoint-ы с РАЗНЫМИ данными!
// Никогда не перепутывать их местами. Используйте РАЗНЫЕ queryKey для каждого!

import { useQuery } from '@tanstack/react-query'
import {
  getAdvertiserAnalytics,
  getOwnerAnalytics,
  getAIInsights,
  type AIInsightsUnifiedResponse,
  type InsightsRole,
} from '@/api/analytics'

export const useAdvertiserAnalytics = () =>
  useQuery({
    queryKey: ['analytics', 'advertiser'],
    queryFn: getAdvertiserAnalytics,
    staleTime: 5 * 60_000,
    retry: 2,
  })

export const useOwnerAnalytics = () =>
  useQuery({
    queryKey: ['analytics', 'owner'],
    queryFn: getOwnerAnalytics,
    staleTime: 5 * 60_000,
    retry: 2,
  })

export const useAIInsights = (role: InsightsRole) =>
  useQuery<AIInsightsUnifiedResponse>({
    queryKey: ['analytics', 'ai-insights', role],
    queryFn: () => getAIInsights(role),
    staleTime: 10 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  })
