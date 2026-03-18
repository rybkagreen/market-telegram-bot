// ВАЖНО (RT-001): advertiser и owner — это РАЗНЫЕ endpoint-ы с РАЗНЫМИ данными!
// Никогда не перепутывать их местами.

import { api } from './client'
import type { AdvertiserAnalytics, OwnerAnalytics } from '@/lib/types'

export function getAdvertiserAnalytics(): Promise<AdvertiserAnalytics> {
  return api.get('analytics/advertiser').json<AdvertiserAnalytics>()
}

export function getOwnerAnalytics(): Promise<OwnerAnalytics> {
  return api.get('analytics/owner').json<OwnerAnalytics>()
}
