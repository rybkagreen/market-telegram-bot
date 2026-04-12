import { api } from './client'
import type { PlacementRequest, PlacementStatus, PublicationFormat } from '@/lib/types'

export interface CreatePlacementData {
  channel_id: number
  publication_format: PublicationFormat
  ad_text: string
  proposed_price: number
  proposed_schedule: string
  is_test?: boolean  // Test mode (admin only)
  test_label?: string | null  // Test label (admin only)
}

export interface UpdatePlacementData {
  action: 'accept' | 'reject' | 'counter' | 'cancel' | 'pay' | 'accept-counter' | 'counter-reply'
  price?: number
  schedule?: string
  comment?: string
}

export interface CampaignStartResponse {
  status: string
  placement_request_id: number
}

export interface CampaignResponse {
  status: string
}

export function getMyPlacements(params?: {
  status?: PlacementStatus
  channel_id?: number
  role?: 'advertiser' | 'owner'
  include_test?: boolean  // Include test campaigns (admin only)
}): Promise<PlacementRequest[]> {
  return api.get('placements/', { searchParams: params ?? {} }).json<PlacementRequest[]>()
}

export function getPlacement(id: number): Promise<PlacementRequest> {
  return api.get(`placements/${id}`).json<PlacementRequest>()
}

export function createPlacement(data: CreatePlacementData): Promise<PlacementRequest> {
  return api.post('placements/', { json: data }).json<PlacementRequest>()
}

export function updatePlacement(id: number, data: UpdatePlacementData): Promise<PlacementRequest> {
  return api.patch(`placements/${id}`, { json: data }).json<PlacementRequest>()
}

export function startCampaign(id: number): Promise<CampaignStartResponse> {
  return api.post(`campaigns/${id}/start`).json<CampaignStartResponse>()
}

export function cancelCampaign(id: number): Promise<CampaignResponse> {
  return api.post(`campaigns/${id}/cancel`).json<CampaignResponse>()
}

export function duplicateCampaign(id: number): Promise<CampaignResponse> {
  return api.post(`campaigns/${id}/duplicate`).json<CampaignResponse>()
}
