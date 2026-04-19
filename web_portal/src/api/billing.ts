import { api } from '@shared/api/client'

export interface TransactionItem {
  id: number
  type: string
  amount: string
  status: string
  description: string | null
  created_at: string
  placement_request_id: number | null
}

export interface TransactionListResponse {
  items: TransactionItem[]
  total: number
  page: number
  pages: number
}

export async function getTransactionHistory(page = 1, limit = 20) {
  return api.get(`billing/history?page=${page}&limit=${limit}`).json<TransactionListResponse>()
}

export interface TopupInitiateResponse {
  payment_id: string
  payment_url: string
  amount: string
  fee: string
  desired_amount: string
}

export async function initiateTopup(desiredAmount: number) {
  return api
    .post('billing/topup', { json: { desired_amount: desiredAmount } })
    .json<TopupInitiateResponse>()
}

export async function getBalance() {
  return api.get('billing/balance').json<{
    balance_rub: string
    earned_rub: string
    plan: string
  }>()
}

export async function getPlans() {
  return api.get('billing/plans').json<Array<{
    id: string
    name: string
    price: number
    features: string[]
    period_days: number
  }>>()
}

export async function purchasePlan(plan: string) {
  return api.post('billing/plan', { json: { plan } }).json<{ success: boolean }>()
}
