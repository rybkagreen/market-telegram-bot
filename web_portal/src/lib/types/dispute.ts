export type DisputeStatus = 'open' | 'owner_explained' | 'resolved' | 'closed'

export type DisputeReason =
  | 'post_removed_early'
  | 'bot_kicked'
  | 'advertiser_complaint'
  | 'not_published'
  | 'wrong_time'
  | 'wrong_text'
  | 'early_deletion'
  | 'other'

export type ResolutionAction =
  | 'owner_fault'
  | 'advertiser_fault'
  | 'technical'
  | 'partial'
  | 'full_refund'
  | 'partial_refund'
  | 'no_refund'
  | 'warning'

export interface DisputeDetailResponse {
  id: number
  placement_request_id: number
  advertiser_id: number
  owner_id: number
  status: DisputeStatus
  reason: DisputeReason
  advertiser_comment: string | null
  owner_explanation: string | null
  resolution: ResolutionAction | null
  resolution_comment: string | null
  admin_id: number | null
  resolved_at: string | null
  advertiser_refund_pct: number | null
  owner_payout_pct: number | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface DisputeListResponse {
  items: DisputeDetailResponse[]
  total: number
  limit: number
  offset: number
}
