import { api } from './client'
import type { ReputationHistory } from './analytics'

export function getReputationHistory(page: number = 1, limit: number = 20): Promise<ReputationHistory> {
  return api.get('reputation/history', { searchParams: { page, limit } }).json<ReputationHistory>()
}
