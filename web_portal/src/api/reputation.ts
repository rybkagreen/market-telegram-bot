import { api } from '@shared/api/client'
import type { ReputationHistoryItem } from '@/lib/types/analytics'

export async function getReputationHistory(limit = 20, offset = 0) {
  return api
    .get('reputation/me/history', { searchParams: { limit, offset } })
    .json<ReputationHistoryItem[]>()
}
