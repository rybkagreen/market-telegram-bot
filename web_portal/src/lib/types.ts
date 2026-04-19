// ═══ Plan type (string union for Plans.tsx) ═══
export type Plan = 'free' | 'starter' | 'pro' | 'business'

// ═══ Plan detail from billing API ═══
export interface PlanDetail {
  id: string
  name: string
  price: number
  features: string[]
}

// ═══ User from /api/auth/me ═══
export interface User {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  plan: Plan
  role: string
  balance_rub: string
  earned_rub: string
  credits: number
  is_admin: boolean
  ai_generations_used: number
  platform_rules_accepted_at?: string | null
  privacy_policy_accepted_at?: string | null
}

// ═══ Auth ═══
export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

// ═══ Channels ═══
export interface ChannelResponse {
  id: number
  telegram_id: number
  title: string
  username: string | null
  member_count: number
  last_er: number
  avg_views: number
  rating: number
  category: string | null
  is_active: boolean
  owner_id: number
  created_at: string
}

export interface ChannelSettingsOut {
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

export interface ChannelWithSettingsOut {
  id: number
  telegram_id: number
  username: string | null
  title: string
  owner_id: number
  member_count: number
  is_test: boolean
  last_er: number
  avg_views: number
  rating: number
  category: string | null
  is_active: boolean
  settings: ChannelSettingsOut
}

// ═══ Placement Request ═══
export type PlacementStatus =
  | 'pending_owner'
  | 'counter_offer'
  | 'pending_payment'
  | 'escrow'
  | 'published'
  | 'cancelled'
  | 'refunded'
  | 'failed'
  | 'failed_permissions'

export interface PlacementRequest {
  id: number
  channel_id: number
  advertiser_id: number
  owner_id: number
  status: PlacementStatus
  publication_format: string
  ad_text: string
  proposed_price: string
  final_price: string | null
  proposed_schedule: string
  final_schedule: string | null
  counter_offer_count: number
  counter_price: string | null
  counter_schedule: string | null
  counter_comment: string | null
  advertiser_counter_price: string | null
  advertiser_counter_schedule: string | null
  advertiser_counter_comment: string | null
  rejection_reason: string | null
  created_at: string
  expires_at: string
  published_at: string | null
  scheduled_delete_at: string | null
  deleted_at: string | null
  channel?: {
    username: string | null
    title: string
  }
  erid: string | null
  has_dispute: boolean
  is_test: boolean
  test_label: string | null
  media_type: string
  tracking_short_code: string | null
  clicks_count: number
  published_reach: number | null
}

// ═══ Contracts ═══
export type ContractStatus = 'draft' | 'pending' | 'signed' | 'expired' | 'cancelled'
export type ContractType =
  | 'owner_service'
  | 'advertiser_campaign'
  | 'platform_rules'
  | 'privacy_policy'
  | 'tax_agreement'
  | 'advertiser_framework'

export interface Contract {
  id: number
  user_id: number
  contract_type: ContractType
  contract_status: ContractStatus
  created_at: string
  signed_at: string | null
  pdf_url: string | null
  kep_requested?: boolean
  kep_request_email?: string | null
}

// ═══ Stats ═══
export interface UserStats {
  reputation: {
    advertiser_score: number | null
    owner_score: number | null
  }
}

// ═══ Analytics ═══
export interface AdvertiserAnalyticsResponse {
  total_spent: number
  total_campaigns: number
  total_reach: number
  avg_ctr: number
  top_channels: Array<{
    channel: {
      id: number
      username: string
      title: string
      member_count: number
    }
    placements: number
    spent: number
    reach: number
    ctr: number
  }>
}

export interface OwnerAnalyticsResponse {
  total_earned: number
  total_publications: number
  avg_rating: number
  channel_count: number
  earnings_period: {
    today: number
    week: number
    month: number
    total: number
  }
  by_channel: Array<{
    id: number
    channel: {
      id: number
      username: string
      title: string
    }
    placements: number
    publications: number
    earned: number
  }>
}

// ═══ Disputes ═══
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

export interface DisputeDetailResponse {
  id: number
  placement_request_id: number
  reason: DisputeReason
  comment: string
  status: DisputeStatus
  created_at: string
  resolved_at: string | null
  resolution: string | null
  placement?: {
    channel: { username: string | null } | null
    ad_text: string
    proposed_price: number
  }
  advertiser_id?: number
  owner_id?: number
  advertiser_comment?: string
  owner_explanation?: string | null
}

export interface DisputeListResponse {
  items: DisputeDetailResponse[]
  total: number
}

// ═══ Feedback ═══
export interface UserFeedback {
  id: number
  user_id: number
  username?: string
  text: string
  status: string
  created_at: string
  response_text: string | null
  responded_at: string | null
}

export interface FeedbackListResponse {
  items: UserFeedback[]
  total: number
}

// ═══ Admin ═══
export interface PlatformStatsResponse {
  users: { total: number; active: number; admins: number }
  placements: { total: number; active: number; completed: number }
  disputes: { total: number; open: number; resolved: number }
  feedback: { total: number; new: number; resolved: number }
  financial: {
    total_topups: number
    total_payouts: number
    net_balance: number
    escrow_reserved: number
    payout_reserved: number
    profit_accumulated: number
  }
}

export interface UserListAdminResponse {
  items: Array<{
    id: number
    telegram_id: number
    username: string | null
    first_name: string
    last_name: string | null
    plan: string
    role: string
    balance_rub: string
    earned_rub: string
    is_admin: boolean
    reputation_score: number | null
    created_at: string
  }>
  total: number
}

export interface UserAdminResponse extends User {
  created_at: string
  updated_at: string
  reputation_score: number | null
  total_placements?: number
  total_channels?: number
}

// ═══ ORD ═══
export type OrdStatus = 'pending' | 'registered' | 'token_received' | 'reported' | 'failed'
