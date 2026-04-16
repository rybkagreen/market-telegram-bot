import type { Plan } from './user'

export type PayoutStatus = 'pending' | 'processing' | 'paid' | 'rejected'

export type OrdStatus = 'pending' | 'registered' | 'token_received' | 'reported' | 'failed'

export interface Payout {
  id: number
  owner_id: number
  gross_amount: string
  fee_amount: string
  net_amount: string
  status: PayoutStatus
  requisites: string
  admin_id: number | null
  processed_at: string | null
  rejection_reason: string | null
  ndfl_withheld: string | null
  npd_status: string | null
  created_at: string
  updated_at: string
}

export interface TopUpRequest {
  desired_amount: number
}

export interface TopUpResponse {
  payment_id: string
  payment_url: string
  amount: string
  fee: string
  total: string
}

export interface PlanInfo {
  key: Plan
  name: string
  price: number
  features: string[]
}

export interface AdminPayout {
  id: number
  owner_id: number
  gross_amount: string
  fee_amount: string
  net_amount: string
  status: PayoutStatus
  requisites: string
  created_at: string
  processed_at: string | null
  rejection_reason: string | null
  ndfl_withheld: string | null
  npd_status: string | null
}

export interface PayoutListAdminResponse {
  items: AdminPayout[]
  total: number
}
