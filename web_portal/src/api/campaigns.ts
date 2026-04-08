import { api } from '@shared/api/client'
import type { ChannelResponse, PlacementRequest } from '@/lib/types'

// ═══ Channels search (for campaign wizard) ═══
export async function searchChannels(params: { category?: string }) {
  const search = new URLSearchParams()
  if (params.category) search.set('category', params.category)
  return api.get(`channels/available?${search}`).json<ChannelResponse[]>()
}

// ═══ Create placement (campaign wizard submit) ═══
export async function createPlacement(data: {
  channel_id: number
  publication_format: string
  ad_text: string
  proposed_price: number
  proposed_schedule?: string
  is_test?: boolean
}) {
  return api.post('placements/', { json: data }).json<PlacementRequest>()
}

// ═══ List placements (advertiser or owner role) ═══
export async function getMyPlacements(params?: { status?: string; role?: 'advertiser' | 'owner' }) {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.role) search.set('role', params.role)
  search.set('page', '1')
  search.set('page_size', '100')
  return api.get(`placements/?${search}`).json<PlacementRequest[]>()
}

// ═══ Get placement by ID ═══
export async function getPlacement(id: number) {
  return api.get(`placements/${id}`).json<PlacementRequest>()
}

// ═══ Update placement ═══
export async function updatePlacement(id: number, data: Record<string, unknown>) {
  return api.patch(`placements/${id}`, { json: data }).json<PlacementRequest>()
}

// ═══ Get placement request (alias) ═══
export async function getPlacementRequest(id: number) {
  return api.get(`placements/${id}`).json<PlacementRequest>()
}

// ═══ Update placement request (alias) ═══
export async function updatePlacementRequest(id: number, data: Record<string, unknown>) {
  return api.patch(`placements/${id}`, { json: data }).json<PlacementRequest>()
}

// ═══ Start campaign ═══
export async function startCampaign(id: number) {
  return api.post(`placements/${id}/start`).json<PlacementRequest>()
}

// ═══ Cancel campaign ═══
export async function cancelCampaign(id: number) {
  return api.post(`placements/${id}/cancel`).json<PlacementRequest>()
}

// ═══ Duplicate campaign ═══
export async function duplicateCampaign(id: number) {
  return api.post(`placements/${id}/duplicate`).json<PlacementRequest>()
}
