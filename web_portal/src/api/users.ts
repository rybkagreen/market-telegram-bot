import { api } from '@shared/api/client'
import type { User, UserStats } from '@/lib/types'
import type { ReferralStats } from '@/lib/types/misc'

export async function getMe() {
  return api.get('users/me').json<User>()
}

export async function getMyStats() {
  return api.get('users/me/stats').json<UserStats>()
}

export async function getReferralStats() {
  return api.get('users/me/referrals').json<ReferralStats>()
}

export async function checkNeedsAcceptRules() {
  return api.get('users/needs-accept-rules').json<{ needs_accept: boolean }>()
}

export type AttentionSeverity = 'danger' | 'warning' | 'info' | 'success'
export type AttentionType =
  | 'legal_profile_incomplete'
  | 'placement_pending_approval'
  | 'new_topup_success'
  | 'channel_verified'
  | 'contract_sign_required'
  | 'payout_ready'
  | 'dispute_requires_response'

export interface AttentionItem {
  type: AttentionType
  severity: AttentionSeverity
  title: string
  subtitle: string | null
  url: string | null
  created_at: string
}

export interface AttentionFeedResponse {
  items: AttentionItem[]
  total: number
}

export async function getAttentionFeed() {
  return api.get('users/me/attention').json<AttentionFeedResponse>()
}
