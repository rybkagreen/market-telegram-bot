import type { OrdStatus } from './billing'

export interface Category {
  key: string
  name: string
  emoji: string
}

export interface AiTextResult {
  variants: string[]
}

export interface ReferralStats {
  referral_code: string
  referral_link: string
  total_referrals: number
  active_referrals: number
  total_earned_rub: string
  referrals: ReferralItem[]
}

export interface ReferralItem {
  id: number
  username: string | null
  telegram_id: number
  is_active: boolean
  created_at: string
}

export interface ReviewResponse {
  id: number
  placement_request_id: number
  reviewer_id: number
  reviewed_id: number
  rating: number
  comment: string | null
  created_at: string
}

export interface PlacementReviewsResponse {
  placement_request_id: number
  my_review: ReviewResponse | null
  their_review: ReviewResponse | null
}

export interface CreateReviewPayload {
  placement_request_id: number
  rating: number
  comment: string
}

export interface ChannelSettings {
  channel_id: number
  price_per_post: string
  allow_format_post_24h: boolean
  allow_format_post_48h: boolean
  allow_format_post_7d: boolean
  allow_format_pin_24h: boolean
  allow_format_pin_48h: boolean
  max_posts_per_day: number
  max_posts_per_week: number
  publish_start_time: string
  publish_end_time: string
  break_start_time: string | null
  break_end_time: string | null
  auto_accept_enabled: boolean
}

export interface ChannelCheckResponse {
  valid: boolean
  channel: {
    id: number
    title: string
    username: string
    member_count: number
  }
  bot_permissions: {
    is_admin: boolean
    post_messages: boolean
    delete_messages: boolean
    pin_messages: boolean
  }
  missing_permissions: string[]
  is_already_added: boolean
  rules_valid: boolean
  rules_violations: string[]
  language_valid: boolean
  language_warnings: string[]
  category: string | null
}

export interface OrdRegistration {
  id: number
  placement_request_id: number
  erid: string | null
  status: OrdStatus
  ord_provider: string
  error_message: string | null
  created_at: string
}
