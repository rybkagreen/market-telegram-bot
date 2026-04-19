export type {
  PayoutStatus,
  PayoutResponse,
  AdminPayoutResponse,
  AdminPayoutListResponse,
  PayoutCreateRequest,
} from './payout'

export type OrdStatus =
  | 'pending'
  | 'registered'
  | 'token_received'
  | 'reported'
  | 'failed'

export interface TopUpRequest {
  desired_amount: number
}

export interface TopUpResponse {
  payment_id: string
  payment_url: string
  amount: string
  fee: string
  desired_amount: string
}

export interface PlanInfo {
  id: string
  name: string
  price: number
  features: string[]
  period_days: number
}
