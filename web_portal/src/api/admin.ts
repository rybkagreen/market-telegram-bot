import { api } from '@shared/api/client'
import type {
  PlatformStatsResponse,
  UserListAdminResponse,
  UserAdminResponse,
} from '@/lib/types'
import type { AdminPayout, PayoutListAdminResponse } from '@/lib/types/billing'

export async function getPlatformStats() {
  return api.get('admin/stats').json<PlatformStatsResponse>()
}

export async function getUsersList(params: {
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params.limit) search.set('limit', String(params.limit))
  if (params.offset) search.set('offset', String(params.offset))
  return api.get(`admin/users?${search}`).json<UserListAdminResponse>()
}

export async function getUserById(userId: number) {
  return api.get(`admin/users/${userId}`).json<UserAdminResponse>()
}

export async function updateAdminUser(userId: number, data: { plan?: string; is_admin?: boolean }) {
  return api.patch(`admin/users/${userId}`, { json: data }).json<UserAdminResponse>()
}

export async function getAdminPayouts(params: {
  status?: string
  limit?: number
  offset?: number
}) {
  const search = new URLSearchParams()
  if (params.status) search.set('status', params.status)
  if (params.limit != null) search.set('limit', String(params.limit))
  if (params.offset != null) search.set('offset', String(params.offset))
  return api.get(`admin/payouts?${search}`).json<PayoutListAdminResponse>()
}

export async function approveAdminPayout(payoutId: number) {
  return api.post(`admin/payouts/${payoutId}/approve`).json<AdminPayout>()
}

export async function rejectAdminPayout(payoutId: number, reason: string) {
  return api.post(`admin/payouts/${payoutId}/reject`, { json: { reason } }).json<AdminPayout>()
}
