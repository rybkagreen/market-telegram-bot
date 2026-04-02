import { api } from './client'
import type { User, ReputationScore, ReferralStats } from '@/lib/types'

export function getMe(): Promise<User> {
  return api.get('users/me').json<User>()
}

export function getMyStats(): Promise<{ reputation: ReputationScore }> {
  return api.get('users/me/stats').json<{ reputation: ReputationScore }>()
}

export function getReferralStats(): Promise<ReferralStats> {
  return api.get('users/me/referrals').json<ReferralStats>()
}
