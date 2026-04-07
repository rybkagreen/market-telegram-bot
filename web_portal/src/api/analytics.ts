import { api } from '@shared/api/client'
import type { AdvertiserAnalyticsResponse, OwnerAnalyticsResponse } from '@/lib/types'

export async function getAdvertiserAnalytics() {
  return api.get('analytics/advertiser').json<AdvertiserAnalyticsResponse>()
}

export async function getOwnerAnalytics() {
  return api.get('analytics/owner').json<OwnerAnalyticsResponse>()
}
