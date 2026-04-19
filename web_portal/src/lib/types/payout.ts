export type PayoutStatus = 'pending' | 'processing' | 'paid' | 'rejected' | 'cancelled'

export interface PayoutResponse {
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
  created_at: string
  updated_at: string
}

export interface AdminPayoutResponse extends PayoutResponse {
  owner_username: string | null
  owner_telegram_id: number | null
}

export interface AdminPayoutListResponse {
  items: AdminPayoutResponse[]
  total: number
  limit: number
  offset: number
}

export interface PayoutCreateRequest {
  amount: number
  payment_details: string
}
