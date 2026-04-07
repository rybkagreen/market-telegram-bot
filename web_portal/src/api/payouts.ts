import { api } from '@shared/api/client'

export interface Payout {
  id: number
  amount: string
  fee: string
  net_amount: string
  status: string
  payment_details: string
  created_at: string
  processed_at: string | null
}

export async function getMyPayouts() {
  return api.get('payouts/my').json<Payout[]>()
}

export async function createPayout(data: { amount: number; payment_details: string }) {
  return api.post('payouts', { json: data }).json<Payout>()
}
