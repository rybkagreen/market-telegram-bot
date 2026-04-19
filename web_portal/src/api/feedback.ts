import { api } from '@shared/api/client'
import type {
  FeedbackListResponse,
  DisputeListResponse,
  FeedbackAdminResponse,
  FeedbackAdminListResponse,
  FeedbackRespondPayload,
  FeedbackStatusUpdatePayload,
  UserFeedback,
} from '@/lib/types'

export async function getMyFeedback() {
  return api.get('feedback/').json<FeedbackListResponse>()
}

export async function createFeedback(text: string) {
  return api.post('feedback/', { json: { text } }).json<UserFeedback>()
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
  return api.get(`feedback/admin/?${search}`).json<FeedbackAdminListResponse>()
}

export async function getAdminFeedbackById(feedbackId: number) {
  return api.get(`feedback/admin/${feedbackId}`).json<FeedbackAdminResponse>()
}

export async function respondToFeedback(feedbackId: number, payload: FeedbackRespondPayload) {
  return api
    .post(`feedback/admin/${feedbackId}/respond`, { json: payload })
    .json<FeedbackAdminResponse>()
}

export async function updateFeedbackStatus(
  feedbackId: number,
  payload: FeedbackStatusUpdatePayload,
) {
  return api
    .patch(`feedback/admin/${feedbackId}/status`, { json: payload })
    .json<FeedbackAdminResponse>()
}
