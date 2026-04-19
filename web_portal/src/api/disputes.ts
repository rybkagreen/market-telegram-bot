import { api } from '@shared/api/client'
import type { DisputeDetailResponse, DisputeListResponse } from '@/lib/types'

export interface PublicationEvidenceEvent {
  id: number
  event_type: string
  message_id: number | null
  post_url: string | null
  erid: string | null
  detected_at: string
  extra: Record<string, unknown> | null
}

export interface DisputeEvidenceSummary {
  published_at: string | null
  deleted_at: string | null
  deletion_type: 'by_bot' | 'early_by_owner' | null
  erid_present: boolean
  total_duration_minutes: number
}

export interface DisputeEvidenceResponse {
  placement_id: number
  channel_id: number | null
  events: PublicationEvidenceEvent[]
  summary: DisputeEvidenceSummary
}

export async function createDispute(data: { placement_id: number; reason: string; comment: string }) {
  return api.post('disputes', { json: data }).json<DisputeDetailResponse>()
}

export async function getMyDisputes(params?: {
  statusFilter?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.statusFilter) search.set('status_filter', params.statusFilter)
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.offset != null) search.set('offset', String(params.offset))
  const qs = search.toString()
  return api.get(qs ? `disputes?${qs}` : 'disputes').json<DisputeListResponse>()
}

export async function getDisputeById(id: number) {
  return api.get(`disputes/${id}`).json<DisputeDetailResponse>()
}

export async function replyToDispute(id: number, comment: string) {
  return api.patch(`disputes/${id}`, { json: { owner_comment: comment } }).json<DisputeDetailResponse>()
}

export async function getDisputeEvidence(placementId: number) {
  return api.get(`disputes/evidence/${placementId}`).json<DisputeEvidenceResponse>()
}

export async function resolveDispute(
  id: number,
  resolution: string,
  adminComment?: string,
  customSplitPercent?: number,
) {
  return api.post(`disputes/admin/disputes/${id}/resolve`, {
    json: {
      resolution,
      admin_comment: adminComment,
      custom_split_percent: customSplitPercent,
    },
  }).json<DisputeDetailResponse>()
}
