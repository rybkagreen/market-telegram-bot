import { api } from '@shared/api/client'

// ─── Types (mirror src/api/schemas/channel_verification.py from Phase B.5a) ──

export interface ChannelVerificationSubmitRequest {
  application_number: string
  registry_url?: string | null
  notes?: string | null
}

export interface ChannelVerificationSubmitResponse {
  status: 'pending_review'
  channel_id: number
  application_number: string
  submitted_at: string
}

export type ChannelVerificationStatus = 'pending_review' | 'verified'

export interface ChannelVerificationListItem {
  channel_id: number
  channel_username: string | null
  channel_title: string | null
  member_count: number
  owner_id: number
  owner_username: string | null
  application_number: string
  submitted_at: string
  status: ChannelVerificationStatus
}

export interface ChannelVerificationListResponse {
  items: ChannelVerificationListItem[]
  total: number
  limit: number
  offset: number
}

export interface ChannelVerificationHistoryEntry {
  action: string
  actor_user_id: number | null
  created_at: string
  extra: Record<string, unknown> | null
}

export interface ChannelVerificationDetailResponse {
  channel_id: number
  channel_username: string | null
  channel_title: string | null
  member_count: number
  owner_id: number
  owner_username: string | null
  is_blogger_registry_verified: boolean
  blogger_registry_verified_at: string | null
  blogger_registry_verification_method: string | null
  blogger_registry_verified_by_admin_id: number | null
  application_number: string | null
  member_count_at_verification: number | null
  last_blogger_registry_check_at: string | null
  history: ChannelVerificationHistoryEntry[]
}

export interface ChannelVerificationVerifyRequest {
  notes?: string | null
}

export interface ChannelVerificationVerifyResponse {
  channel_id: number
  is_blogger_registry_verified: true
  blogger_registry_verified_at: string
  blogger_registry_verification_method: 'manual_evidence'
  blogger_registry_verified_by_admin_id: number
}

export interface ChannelVerificationRejectRequest {
  reason: string
  internal_notes?: string | null
}

export interface ChannelVerificationRejectResponse {
  channel_id: number
  rejected_at: string
  reason: string
}

// ─── API functions ──────────────────────────────────────────────────────────

export async function listChannelVerifications(params?: {
  status?: ChannelVerificationStatus
  ownerId?: number
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.ownerId != null) search.set('owner_id', String(params.ownerId))
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const qs = search.toString()
  return api
    .get(qs ? `admin/channel-verifications?${qs}` : 'admin/channel-verifications')
    .json<ChannelVerificationListResponse>()
}

export async function getChannelVerificationDetail(channelId: number) {
  return api
    .get(`admin/channel-verifications/${channelId}`)
    .json<ChannelVerificationDetailResponse>()
}

export async function verifyChannelManually(
  channelId: number,
  body: ChannelVerificationVerifyRequest,
) {
  return api
    .post(`admin/channel-verifications/${channelId}/verify`, { json: body })
    .json<ChannelVerificationVerifyResponse>()
}

export async function rejectChannelVerification(
  channelId: number,
  body: ChannelVerificationRejectRequest,
) {
  return api
    .post(`admin/channel-verifications/${channelId}/reject`, { json: body })
    .json<ChannelVerificationRejectResponse>()
}
