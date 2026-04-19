import type { DisputeStatus } from './dispute'

export type PlacementStatus =
  | 'pending_owner'
  | 'counter_offer'
  | 'pending_payment'
  | 'escrow'
  | 'published'
  | 'failed'
  | 'failed_permissions'
  | 'refunded'
  | 'cancelled'

export type PublicationFormat = 'post_24h' | 'post_48h' | 'post_7d' | 'pin_24h' | 'pin_48h'

export type MediaType = 'none' | 'photo' | 'video'

export interface PlacementRequest {
  id: number
  advertiser_id: number
  owner_id: number
  channel_id: number
  channel?: { id: number; username: string; title: string; member_count: number }
  status: PlacementStatus
  publication_format: PublicationFormat
  ad_text: string
  proposed_price: string
  final_price: string | null
  proposed_schedule: string
  final_schedule: string | null
  counter_offer_count: number
  counter_price: string | null
  counter_schedule: string | null
  counter_comment: string | null
  rejection_reason: string | null
  expires_at: string
  published_at: string | null
  scheduled_delete_at: string | null
  deleted_at: string | null
  clicks_count: number
  published_reach: number | null
  tracking_short_code: string | null
  has_dispute: boolean
  dispute_status: DisputeStatus | null
  is_test: boolean
  test_label: string | null
  media_type: MediaType
  video_file_id: string | null
  video_url: string | null
  video_thumbnail_file_id: string | null
  video_duration: number | null
  erid: string | null
  created_at: string
}
