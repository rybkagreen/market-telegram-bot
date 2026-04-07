import { api } from '@shared/api/client'
import type { DisputeDetailResponse, DisputeListResponse } from '@/lib/types'

export async function createDispute(data: { placement_id: number; reason: string; comment: string }) {
  return api.post('disputes', { json: data }).json<DisputeDetailResponse>()
}

export async function getMyDisputes() {
  return api.get('disputes').json<DisputeListResponse>()
}

export async function getDisputeById(id: number) {
  return api.get(`disputes/${id}`).json<DisputeDetailResponse>()
}

export async function replyToDispute(id: number, comment: string) {
  return api.patch(`disputes/${id}`, { json: { owner_comment: comment } }).json<DisputeDetailResponse>()
}

export async function resolveDispute(id: number, resolution: string, adminComment?: string) {
  return api.post(`disputes/admin/disputes/${id}/resolve`, {
    json: { resolution, admin_comment: adminComment },
  }).json<DisputeDetailResponse>()
}
