/**
 * Admin API client functions
 *
 * All functions require authentication via JWT token.
 * The token is automatically added by the ky interceptors.
 */

import { api } from '@/api/client'
import type {
  FeedbackAdminResponse,
  FeedbackListAdminResponse,
  FeedbackRespondRequest as TypesFeedbackRespondRequest,
  FeedbackStatusUpdateRequest as TypesFeedbackStatusUpdateRequest,
  DisputeAdminResponse,
  DisputeListAdminResponse,
  DisputeResolveRequest as TypesDisputeResolveRequest,
  UserAdminResponse,
  UserListAdminResponse,
  PlatformStatsResponse,
} from '@/lib/types'

// Re-export types for hooks
export type FeedbackRespondRequest = TypesFeedbackRespondRequest
export type FeedbackStatusUpdateRequest = TypesFeedbackStatusUpdateRequest
export type DisputeResolveRequest = TypesDisputeResolveRequest

// ============================================================
// Feedback API
// ============================================================

export interface FeedbackListParams {
  status?: string
  limit?: number
  offset?: number
}

export function getFeedbackList(params: FeedbackListParams): Promise<FeedbackListAdminResponse> {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.append('status_filter', params.status)
  if (params.limit) searchParams.append('limit', params.limit.toString())
  if (params.offset !== undefined) searchParams.append('offset', params.offset.toString())

  return api.get('feedback/admin/', { searchParams }).json<FeedbackListAdminResponse>()
}

export function getFeedbackById(id: number): Promise<FeedbackAdminResponse> {
  return api.get(`feedback/admin/${id}`).json<FeedbackAdminResponse>()
}

export function respondToFeedback(
  id: number,
  data: FeedbackRespondRequest
): Promise<FeedbackAdminResponse> {
  return api.post(`feedback/admin/${id}/respond`, { json: data }).json<FeedbackAdminResponse>()
}

export function updateFeedbackStatus(
  id: number,
  data: FeedbackStatusUpdateRequest
): Promise<FeedbackAdminResponse> {
  return api.patch(`feedback/admin/${id}/status`, { json: data }).json<FeedbackAdminResponse>()
}

// ============================================================
// Disputes API
// ============================================================

export interface DisputesListParams {
  status?: string
  limit?: number
  offset?: number
}

export function getDisputesList(params: DisputesListParams): Promise<DisputeListAdminResponse> {
  const searchParams = new URLSearchParams()
  if (params.status) searchParams.append('status_filter', params.status)
  if (params.limit) searchParams.append('limit', params.limit.toString())
  if (params.offset !== undefined) searchParams.append('offset', params.offset.toString())

  return api.get('disputes/admin/disputes', { searchParams }).json<DisputeListAdminResponse>()
}

export function getDisputeById(id: number): Promise<DisputeAdminResponse> {
  return api.get(`disputes/admin/disputes/${id}`).json<DisputeAdminResponse>()
}

export function resolveDispute(
  id: number,
  data: DisputeResolveRequest
): Promise<DisputeAdminResponse> {
  return api.post(`disputes/admin/disputes/${id}/resolve`, { json: data }).json<DisputeAdminResponse>()
}

// ============================================================
// Stats API
// ============================================================

export function getPlatformStats(): Promise<PlatformStatsResponse> {
  return api.get('admin/stats').json<PlatformStatsResponse>()
}

// ============================================================
// Users API
// ============================================================

export interface UsersListParams {
  role?: string
  limit?: number
  offset?: number
}

export function getUsersList(params: UsersListParams): Promise<UserListAdminResponse> {
  const searchParams = new URLSearchParams()
  if (params.role) searchParams.append('role', params.role)
  if (params.limit) searchParams.append('limit', params.limit.toString())
  if (params.offset !== undefined) searchParams.append('offset', params.offset.toString())

  return api.get('admin/users', { searchParams }).json<UserListAdminResponse>()
}

export function getUserById(id: number): Promise<UserAdminResponse> {
  return api.get(`admin/users/${id}`).json<UserAdminResponse>()
}
