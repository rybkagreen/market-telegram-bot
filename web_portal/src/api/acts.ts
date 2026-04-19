import { api } from '@shared/api/client'

export interface Act {
  id: number
  placement_request_id: number
  sign_status: 'draft' | 'pending' | 'signed' | 'auto_signed'
  signed_at: string | null
  created_at: string
  amount: string
  act_number: string | null
}

export interface ActListResponse {
  items: Act[]
  total: number
}

export async function getPlacementActs(placementId: number) {
  return api
    .get(`acts/mine?placement_request_id=${placementId}`)
    .json<ActListResponse>()
}

export async function signAct(actId: number) {
  return api.post(`acts/${actId}/sign`).json<Act>()
}
