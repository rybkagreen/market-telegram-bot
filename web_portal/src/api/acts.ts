import { api } from '@shared/api/client'

export interface Act {
  id: number
  act_number: string | null
  act_type: string
  act_date: string | null
  sign_status: 'draft' | 'pending' | 'signed' | 'auto_signed'
  signed_at: string | null
  sign_method: string | null
  pdf_url: string | null
  placement_request_id: number
  created_at: string
}

export interface ActListResponse {
  items: Act[]
  total: number
}

export async function getMyActs(params?: { limit?: number; placementRequestId?: number }) {
  const search = new URLSearchParams()
  if (params?.limit != null) search.set('limit', String(params.limit))
  if (params?.placementRequestId != null) search.set('placement_request_id', String(params.placementRequestId))
  const qs = search.toString()
  return api.get(qs ? `acts/mine?${qs}` : 'acts/mine').json<ActListResponse>()
}

export async function getPlacementActs(placementId: number) {
  return getMyActs({ placementRequestId: placementId })
}

export async function signAct(actId: number) {
  return api.post(`acts/${actId}/sign`).json<Act>()
}

export async function getActPdfBlob(actId: number) {
  return api.get(`acts/${actId}/pdf`, { timeout: 30_000 }).blob()
}
