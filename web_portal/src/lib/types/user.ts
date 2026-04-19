export type Plan = 'free' | 'starter' | 'pro' | 'business'

export interface User {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  plan: Plan
  plan_expires_at: string | null
  balance_rub: string
  earned_rub: string
  credits: number
  advertiser_xp: number
  advertiser_level: number
  owner_xp: number
  owner_level: number
  referral_code: string | null
  is_admin: boolean
  ai_generations_used: number
  legal_status_completed: boolean
  has_legal_profile: boolean
  legal_profile_prompted_at: string | null
  legal_profile_skipped_at: string | null
  platform_rules_accepted_at: string | null
  privacy_policy_accepted_at: string | null
}

export interface AuthResponse {
  access_token: string
  user: User
}

export interface UserAdminResponse {
  id: number
  telegram_id: number
  username: string | null
  first_name: string
  last_name: string | null
  plan: Plan
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
