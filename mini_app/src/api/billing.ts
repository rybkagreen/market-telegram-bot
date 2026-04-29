import { api } from './client'
import type { Plan, TopUpResponse } from '@/lib/types'

export interface PlanDetail {
  key: Plan
  name: string
  price: number
  features: string[]
}

export interface BillingBalance {
  balance_rub: string
  plan: string
  plan_expires_at: string | null
  ai_generations_used: number
  ai_included: number
  plan_costs: Record<string, number>
}

// Типы, реально присутствующие в БД (+ payout синтезируется на бэкенде из refund_full+meta)
export type TransactionType =
  | 'topup'
  | 'escrow_freeze'
  | 'escrow_release'
  | 'spend'
  | 'payout'
  | 'payout_fee'
  | 'refund_full'
  | 'bonus'

export interface BillingHistoryItem {
  id: number
  type: TransactionType | string
  amount: number
  description: string | null
  placement_request_id: number | null
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
  balance_rub_remaining: number
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

export interface BuyCreditsResponse {
  amount_rub: number
}

export function buyCredits(amountRub: number): Promise<BuyCreditsResponse> {
  return api.post('billing/credits', { json: { desired_amount: amountRub } }).json<BuyCreditsResponse>()
}

export interface FeeConfigResponse {
  topup: { yookassa_fee_rate: string }
  placement: {
    platform_commission_rate: string
    owner_share_rate: string
    service_fee_rate: string
    owner_net_rate: string
    platform_total_rate: string
  }
  cancel: {
    advertiser_rate: string
    owner_rate: string
    platform_rate: string
  }
}

export function getFeeConfig(): Promise<FeeConfigResponse> {
  return api.get('billing/fee-config').json<FeeConfigResponse>()
}
