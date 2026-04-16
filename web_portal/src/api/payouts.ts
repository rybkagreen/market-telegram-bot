import { api } from '@shared/api/client'
import type { Payout } from '@/lib/types/billing'

export async function getMyPayouts() {
  return api.get('payouts/').json<Payout[]>()
}

export async function createPayout(data: { gross_amount: number; requisites: string }) {
  return api.post('payouts', { json: data }).json<Payout>()
}
