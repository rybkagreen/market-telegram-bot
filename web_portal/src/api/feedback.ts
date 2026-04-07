import { api } from '@shared/api/client'
import type { UserFeedback, FeedbackListResponse, DisputeListResponse } from '@/lib/types'

export async function getMyFeedback() {
  return api.get('feedback/').json<FeedbackListResponse>()
}

export async function getAdminDisputes(params?: {
  status?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  return api.get(`disputes/admin/disputes?${search}`).json<DisputeListResponse>()
}

export async function getAdminFeedback(params?: {
  status?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.limit) search.set('limit', String(params.limit))
  if (params?.offset) search.set('offset', String(params.offset))
  return api.get(`feedback/admin/?${search}`).json<{ items: UserFeedback[]; total: number; limit: number; offset: number }>()
}
