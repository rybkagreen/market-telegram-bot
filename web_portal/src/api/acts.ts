// ============================================================
// RekHarbor Web Portal — Acts API Client
// S31-04 | GET /api/acts/* endpoints
// ============================================================

import { api } from '@shared/api/client'

export interface Act {
  id: number
  placement_request_id: number
  act_number: string | null
  sign_status: string  // draft | pending | signed | auto_signed
  pdf_file_path: string | null
  signed_at: string | null
  created_at: string
}

export interface ActListResponse {
  items: Act[]
  total: number
}

export const getMyActs = (): Promise<ActListResponse> =>
  api.get('acts/mine').json<ActListResponse>()

export const getActsByPlacement = (placementRequestId: number): Promise<ActListResponse> =>
  api.get(`acts/by-placement/${placementRequestId}`).json<ActListResponse>()

export const getActById = (actId: number): Promise<Act> =>
  api.get(`acts/${actId}`).json<Act>()

export const signAct = (actId: number): Promise<Act> =>
  api.post(`acts/${actId}/sign`).json<Act>()

export const getActPdfUrl = (actId: number): string =>
  `/api/acts/${actId}/pdf`
