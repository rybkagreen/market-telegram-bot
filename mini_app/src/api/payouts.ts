import { api } from './client'
import type { Payout } from '@/lib/types'

export function getPayouts(): Promise<Payout[]> {
  return api.get('payouts/').json<Payout[]>()
}

export function createPayout(data: {
  amount: number
  payment_details: string
}): Promise<Payout> {
  return api.post('payouts/', { json: data }).json<Payout>()
}
