import { useQuery } from '@tanstack/react-query'
import {
  getAdvertiserAnalytics,
  getOwnerAnalytics,
  getCashflow,
  getAIInsights,
  type CashflowDays,
  type InsightsRole,
  type AIInsightsUnifiedResponse,
} from '@/api/analytics'

export function useAdvertiserAnalytics() {
  return useQuery({
    queryKey: ['analytics', 'advertiser'],
    queryFn: getAdvertiserAnalytics,
    staleTime: 30_000,
  })
}

export function useOwnerAnalytics() {
  return useQuery({
    queryKey: ['analytics', 'owner'],
    queryFn: getOwnerAnalytics,
    staleTime: 30_000,
  })
}

export function useCashflow(days: CashflowDays = 30) {
  return useQuery({
    queryKey: ['analytics', 'cashflow', days],
    queryFn: () => getCashflow(days),
    staleTime: 60_000,
  })
}

export function useAIInsights(role: InsightsRole) {
  return useQuery<AIInsightsUnifiedResponse>({
    queryKey: ['analytics', 'ai-insights', role],
    queryFn: () => getAIInsights(role),
    staleTime: 10 * 60_000,
    refetchOnWindowFocus: false,
  })
}
