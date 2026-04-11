// ============================================================
// RekHarbor Mini App — TypeScript Types
// Phase 3
// ============================================================

export type UserRole = 'new' | 'advertiser' | 'owner' | 'both'

export type Plan = 'free' | 'starter' | 'pro' | 'business'

export type PlacementStatus =
  | 'pending_owner'
  | 'counter_offer'
  | 'pending_payment'
  | 'escrow'
  | 'published'
  | 'completed'
  | 'failed'
  | 'failed_permissions'
  | 'refunded'
  | 'cancelled'

export type PublicationFormat =
  | 'post_24h'
  | 'post_48h'
  | 'post_7d'
  | 'pin_24h'
  | 'pin_48h'

export type PayoutStatus = 'pending' | 'processing' | 'paid' | 'rejected'

export type DisputeStatus = 'open' | 'owner_explained' | 'resolved' | 'closed'

export type MediaType = 'none' | 'photo' | 'video'

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

// ---- Entities ----

export interface User {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  current_role: UserRole
  plan: Plan
  plan_expires_at: string | null
  balance_rub: string
  earned_rub: string
  credits: number
  advertiser_xp: number
  advertiser_level: number
  owner_xp: number
  owner_level: number
  referral_code: string
  is_admin: boolean
  legal_status_completed: boolean
  legal_profile_prompted_at: string | null
  legal_profile_skipped_at: string | null
  platform_rules_accepted_at: string | null
  privacy_policy_accepted_at: string | null
  has_legal_profile: boolean
}

export interface ReputationScore {
  user_id: number
  advertiser_score: number
  owner_score: number
  is_advertiser_blocked: boolean
  is_owner_blocked: boolean
  advertiser_blocked_until: string | null
  owner_blocked_until: string | null
}

export interface ChannelRef {
  id: number
  username: string
  title: string
}

export interface Channel {
  id: number
  telegram_id: number
  username: string
  title: string
  owner_id: number
  member_count: number
  is_test: boolean  // Test mode flag
  // ... existing fields
  last_er: number
  avg_views: number
  rating: number
  category: string
  is_active: boolean
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
  // Phase 3 fields
  rules_valid: boolean
  rules_violations: string[]
  language_valid: boolean
  language_warnings: string[]
  category: string | null
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

export interface PlacementRequest {
  id: number
  advertiser_id: number
  owner_id: number
  channel_id: number
  channel?: ChannelRef
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
  advertiser_counter_price: string | null
  advertiser_counter_schedule: string | null
  advertiser_counter_comment: string | null
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
  is_test: boolean  // Test mode flag
  test_label: string | null  // Test label
  media_type: MediaType
  video_file_id: string | null
  video_url: string | null
  video_thumbnail_file_id: string | null
  video_duration: number | null
  erid: string | null
  created_at: string
}

export interface Payout {
  id: number
  amount: string
  fee: string
  net_amount: string
  status: PayoutStatus
  payment_details: string
  created_at: string
  processed_at: string | null
}

export interface Dispute {
  id: number
  placement_id: number
  placement?: PlacementRequest
  advertiser_id: number
  owner_id: number
  status: DisputeStatus
  reason: DisputeReason
  advertiser_comment: string
  owner_comment: string | null
  resolution: string | null
  resolution_action: ResolutionAction | null
  created_at: string
  resolved_at: string | null
  expires_at: string
}

export interface Category {
  key: string
  name: string
  emoji: string
}

// ---- API shapes ----

export interface AuthResponse {
  access_token: string
  user: User
}

export interface ApiError {
  detail: string
  status_code: number
}

export interface AiTextResult {
  variants: string[]
}

// ---- Analytics ----

export interface AdvertiserAnalytics {
  total_campaigns: number
  total_reach: number
  total_spent: string
  avg_ctr: number
  top_channels: Array<{ channel: Channel; reach: number; ctr: number }>
  by_category: Array<{ category: string; count: number; percentage: number }>
}

export interface OwnerAnalytics {
  total_earned: string
  total_publications: number
  avg_rating: number
  channel_count: number
  by_channel: Array<{ channel: Channel; earned: string; publications: number }>
  earnings_period: { today: string; week: string; month: string; total: string }
}

// ---- Billing ----

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

// ---- Feedback ----

export interface UserFeedback {
  id: number
  user_id: number
  text: string
  status: 'new' | 'in_progress' | 'resolved' | 'rejected'
  admin_response: string | null
  created_at: string
  responded_at: string | null
}

export interface FeedbackCreateRequest {
  text: string
}

export interface FeedbackListResponse {
  items: UserFeedback[]
  total: number
}

// ---- Referral Program ----

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

// ============================================================
// Admin Panel Types (PHASE-3)
// ============================================================

export interface FeedbackAdminResponse {
  id: number
  user_id: number
  username: string | null
  text: string
  status: string
  admin_response: string | null
  responder_username: string | null
  responder_id: number | null
  created_at: string
  responded_at: string | null
}

export interface FeedbackListAdminResponse {
  items: FeedbackAdminResponse[]
  total: number
  limit: number
  offset: number
}

export interface FeedbackRespondRequest {
  response_text: string
  status: string
}

export interface FeedbackStatusUpdateRequest {
  status: string
}

export interface DisputeAdminResponse {
  id: number
  placement_request_id: number
  advertiser_id: number
  owner_id: number
  advertiser_username: string | null
  owner_username: string | null
  reason: string
  status: string
  owner_explanation: string | null
  advertiser_comment: string | null
  resolution: string | null
  resolution_comment: string | null
  admin_id: number | null
  resolved_at: string | null
  advertiser_refund_pct: number | null
  owner_payout_pct: number | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface DisputeListAdminResponse {
  items: DisputeAdminResponse[]
  total: number
  limit: number
  offset: number
}

export interface DisputeResolveRequest {
  resolution: string
  admin_comment?: string
  custom_split_percent?: number
}

export interface UserAdminResponse {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  role: string
  plan: string
  plan_expires_at: string | null
  balance_rub: string
  earned_rub: string
  credits: number
  is_admin: boolean
  advertiser_xp: number
  advertiser_level: number
  owner_xp: number
  owner_level: number
  total_placements: number
  total_channels: number
  total_feedback: number
  total_disputes: number
  reputation_score: number | null
  created_at: string
  updated_at: string
}

export interface UserListAdminResponse {
  items: UserAdminResponse[]
  total: number
  limit: number
  offset: number
}

export interface PlatformStatsResponse {
  users: {
    total: number
    active: number
    admins: number
  }
  feedback: {
    total: number
    new: number
    in_progress: number
    resolved: number
    rejected: number
  }
  disputes: {
    total: number
    open: number
    owner_explained: number
    resolved: number
  }
  placements: {
    total: number
    pending: number
    active: number
    completed: number
    cancelled: number
  }
  financial: {
    total_topups: string
    total_payouts: string
    net_balance: string
    escrow_reserved: string
    payout_reserved: string
    profit_accumulated: string
    // backward-compat aliases
    total_revenue: string
    pending_payouts: string
  }
}

// ============================================================
// S5 ADDITIONS — Document Automation & Video Support
// ============================================================

export type LegalStatus =
  | 'legal_entity'
  | 'individual_entrepreneur'
  | 'self_employed'
  | 'individual'

export type TaxRegime =
  | 'osno' | 'usn' | 'usn_d' | 'usn_dr' | 'patent' | 'npd' | 'ndfl'

export type ContractType =
  | 'owner_service'
  | 'advertiser_campaign'
  | 'advertiser_framework'
  | 'platform_rules'
  | 'privacy_policy'
  | 'tax_agreement'

export type ContractRole = 'owner' | 'advertiser'

export interface ContractSignatureInfo {
  requires_kep: boolean
  kep_requested: boolean
  kep_message: string | null
  can_proceed: boolean
}

export type ContractStatus = 'draft' | 'pending' | 'signed' | 'expired' | 'cancelled'
export type SignatureMethod = 'button_accept' | 'sms_code'
export type OrdStatus = 'pending' | 'registered' | 'token_received' | 'reported' | 'failed'

export interface LegalProfile {
  id: number
  user_id: number
  legal_status: LegalStatus
  inn: string | null
  kpp: string | null
  ogrn: string | null
  ogrnip: string | null
  legal_name: string | null
  address: string | null
  tax_regime: TaxRegime | null
  bank_name: string | null
  bank_account: string | null
  bank_bik: string | null
  bank_corr_account: string | null
  yoomoney_wallet: string | null
  has_passport_data: boolean
  has_inn_scan: boolean
  has_passport_scan: boolean
  has_self_employed_cert: boolean
  has_company_doc: boolean
  is_verified: boolean
  is_complete: boolean
  created_at: string
  updated_at: string
}

export interface LegalProfileCreate {
  legal_status: LegalStatus
  inn?: string
  kpp?: string
  ogrn?: string
  ogrnip?: string
  legal_name?: string
  address?: string
  tax_regime?: TaxRegime
  bank_name?: string
  bank_account?: string
  bank_bik?: string
  bank_corr_account?: string
  yoomoney_wallet?: string
  passport_series?: string
  passport_number?: string
  passport_issued_by?: string
  passport_issue_date?: string
}

export interface Contract {
  id: number
  user_id: number
  contract_type: ContractType
  contract_status: ContractStatus
  placement_request_id: number | null
  template_version: string
  signature_method: SignatureMethod | null
  signed_at: string | null
  expires_at: string | null
  pdf_url: string | null
  kep_requested: boolean
  kep_request_email: string | null
  role: string | null
  created_at: string
  updated_at: string
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

export interface RequiredFields {
  fields: string[]
  scans: string[]
  show_bank_details: boolean
  show_passport: boolean
  show_yoomoney: boolean
  tax_regime_required: boolean
}

// ============================================================
// Reviews
// ============================================================

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
