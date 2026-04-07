import { api } from '@shared/api/client'
import type { ReputationHistory } from '@/lib/types/analytics'

export async function getReputationHistory(page = 1, limit = 20) {
  return api.get('reputation/history', { searchParams: { page, limit } }).json<ReputationHistory>()
}
