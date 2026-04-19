import { api } from '@shared/api/client'
import type { PayoutResponse, PayoutCreateRequest } from '@/lib/types/payout'

export type { PayoutResponse, PayoutCreateRequest }

export async function getMyPayouts() {
  return api.get('payouts/').json<PayoutResponse[]>()
}

export async function createPayout(data: PayoutCreateRequest) {
  return api.post('payouts', { json: data }).json<PayoutResponse>()
}
