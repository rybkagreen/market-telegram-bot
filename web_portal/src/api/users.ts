import { api } from '@shared/api/client'
import type { User, UserStats } from '@/lib/types'
import type { ReferralStats } from '@/lib/types/misc'

export async function getMe() {
  return api.get('users/me').json<User>()
}

export async function getMyStats() {
  return api.get('users/me/stats').json<UserStats>()
}

export async function getReferralStats() {
  return api.get('users/me/referrals').json<ReferralStats>()
}
