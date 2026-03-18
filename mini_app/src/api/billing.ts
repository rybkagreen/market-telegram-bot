import { api } from './client'
import type { Plan, TopUpResponse } from '@/lib/types'

export interface PlanDetail {
  key: Plan
  name: string
  price: number
  features: string[]
}

export function createTopUp(desiredAmount: number): Promise<TopUpResponse> {
  return api.post('billing/topup', { json: { desired_amount: desiredAmount } }).json<TopUpResponse>()
}

export function getTopUpStatus(
  paymentId: string,
): Promise<{ status: 'pending' | 'succeeded' | 'canceled' }> {
  return api
    .get(`billing/topup/${paymentId}/status`)
    .json<{ status: 'pending' | 'succeeded' | 'canceled' }>()
}

export function getPlans(): Promise<PlanDetail[]> {
  return api.get('billing/plans').json<PlanDetail[]>()
}
