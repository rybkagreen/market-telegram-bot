import { api } from './client'
import type { PlacementRequest, PlacementStatus, PublicationFormat } from '@/lib/types'

export interface CreatePlacementData {
  channel_id: number
  publication_format: PublicationFormat
  ad_text: string
  proposed_price: number
  proposed_schedule: string
}

export interface UpdatePlacementData {
  action: 'accept' | 'reject' | 'counter' | 'cancel'
  price?: number
  schedule?: string
  comment?: string
}

export function getMyPlacements(params?: {
  status?: PlacementStatus
  channel_id?: number
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
