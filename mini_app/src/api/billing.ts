import { api } from './client'
import type { Plan, TopUpResponse } from '@/lib/types'

export interface PlanDetail {
  key: Plan
  name: string
  price: number
  features: string[]
}

export interface TopupPackage {
  id: string
  credits: number
  bonus: number
  label: string
  total_credits: number
}

export interface BillingBalance {
  credits: number
  plan: string
  plan_expires_at: string | null
  ai_generations_used: number
  ai_included: number
  packages: TopupPackage[]
  plan_costs: Record<string, number>
}

export interface BillingHistoryItem {
  id: string
  type: string
  amount: number
  credits: number | null
  plan: string | null
  status: string
  created_at: string
}

export interface BillingHistory {
  items: BillingHistoryItem[]
  total: number
  page: number
  pages: number
}

export interface PlanPurchaseRequest {
  plan: string
}

export interface PlanPurchaseResponse {
  success: boolean
  plan: string
  credits_remaining: number
  message: string
}

export function getBillingBalance(): Promise<BillingBalance> {
  return api.get('billing/balance').json<BillingBalance>()
}

export function getBillingHistory(page: number = 1, limit: number = 20): Promise<BillingHistory> {
  return api.get('billing/history', { searchParams: { page, limit } }).json<BillingHistory>()
}

export function purchasePlan(plan: string): Promise<PlanPurchaseResponse> {
  return api.post('billing/plan', { json: { plan } }).json<PlanPurchaseResponse>()
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
