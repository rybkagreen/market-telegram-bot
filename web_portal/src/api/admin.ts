import { api } from '@shared/api/client'
import type {
  PlatformStatsResponse,
  UserListAdminResponse,
  UserAdminResponse,
} from '@/lib/types'

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
