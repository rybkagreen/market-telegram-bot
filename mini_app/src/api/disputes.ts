import { api } from './client'
import type { Dispute, DisputeReason } from '@/lib/types'

/** Map backend DisputeResponse → frontend Dispute shape */
function mapDispute(raw: any): Dispute {
  return {
    id: raw.id,
    placement_id: raw.placement_request_id,
    placement: undefined, // nested placement not provided by API — fetched separately
    advertiser_id: raw.advertiser_id,
    owner_id: raw.owner_id,
    status: raw.status,
    reason: raw.reason,
    advertiser_comment: raw.advertiser_comment ?? '',
    owner_comment: raw.owner_explanation ?? null,
    resolution: raw.resolution_comment ?? raw.resolution ?? null,
    resolution_action: raw.resolution ?? null,
    created_at: raw.created_at,
    resolved_at: raw.resolved_at ?? null,
    expires_at: raw.expires_at ?? new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  }
}

export function getMyDisputes(): Promise<Dispute[]> {
  return api.get('disputes/').json<any[]>().then((items) => items.map(mapDispute))
}

export function createDispute(data: {
  placement_id: number
  reason: DisputeReason
  comment: string
}): Promise<Dispute> {
  return api.post('disputes/', { json: data }).json<any>().then(mapDispute)
}

export function getDispute(id: number): Promise<Dispute> {
  return api.get(`disputes/${id}`).json<any>().then(mapDispute)
}

export function replyToDispute(id: number, comment: string): Promise<Dispute> {
  return api.patch(`disputes/${id}`, { json: { owner_comment: comment } }).json<any>().then(mapDispute)
}
