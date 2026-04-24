import { api } from '@shared/api/client'
import type {
  AdvertiserAnalyticsResponse,
  OwnerAnalyticsResponse,
} from '@/lib/types'

export async function getAdvertiserAnalytics() {
  return api.get('analytics/advertiser').json<AdvertiserAnalyticsResponse>()
}

export async function getOwnerAnalytics() {
  return api.get('analytics/owner').json<OwnerAnalyticsResponse>()
}

export type InsightsRole = 'advertiser' | 'owner'

export interface InsightsActionItem {
  kind: 'reallocate' | 'pause' | 'scale' | 'experiment' | 'optimize' | 'other'
  title: string
  description: string
  impact_estimate: string | null
  channel_id: number | null
  cta_type: 'create_campaign' | 'open_channel' | 'open_placement' | 'none'
}

export interface InsightsForecast {
  period_days: number
  metric: 'earnings' | 'spend' | 'reach' | 'ctr'
  expected_value: string
  confidence_pct: number
}

export interface InsightsAnomaly {
  kind:
    | 'ctr_drop'
    | 'ctr_spike'
    | 'reach_drop'
    | 'earnings_drop'
    | 'inactive_channel'
    | 'other'
  channel_id: number | null
  severity: 'low' | 'medium' | 'high'
  description: string
}

export interface InsightsChannelFlag {
  channel_id: number
  flag: 'hot' | 'warn' | 'idle' | 'neutral'
  reason: string
}

export interface AIInsightsUnifiedResponse {
  role: InsightsRole
  summary: string
  action_items: InsightsActionItem[]
  forecast: InsightsForecast | null
  anomalies: InsightsAnomaly[]
  channel_flags: InsightsChannelFlag[]
  ai_backend: 'mistral' | 'rules'
  generated_at: string
  cache_ttl_seconds: number
}

export async function getAIInsights(
  role: InsightsRole,
  options: { nocache?: boolean } = {},
): Promise<AIInsightsUnifiedResponse> {
  const params = new URLSearchParams({ role })
  if (options.nocache) params.set('nocache', 'true')
  return api
    .get(`analytics/ai-insights?${params.toString()}`)
    .json<AIInsightsUnifiedResponse>()
}

export type CashflowDays = 7 | 30 | 90

export interface CashflowDataPoint {
  date: string
  income: string
  expense: string
}

export interface CashflowResponse {
  period_days: number
  total_income: string
  total_expense: string
  net: string
  points: CashflowDataPoint[]
}

export async function getCashflow(days: CashflowDays = 30) {
  return api.get(`analytics/cashflow?days=${days}`).json<CashflowResponse>()
}
