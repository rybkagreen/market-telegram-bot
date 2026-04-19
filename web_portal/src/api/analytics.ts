import { api } from '@shared/api/client'
import type { AdvertiserAnalyticsResponse, OwnerAnalyticsResponse } from '@/lib/types'

export async function getAdvertiserAnalytics() {
  return api.get('analytics/advertiser').json<AdvertiserAnalyticsResponse>()
}

export async function getOwnerAnalytics() {
  return api.get('analytics/owner').json<OwnerAnalyticsResponse>()
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
