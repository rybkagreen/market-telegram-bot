import { useQuery } from '@tanstack/react-query'
import type { User, UserStats } from '@/lib/types'
import type { ReferralStats } from '@/lib/types/misc'
import { getMe, getMyStats, getReferralStats, checkNeedsAcceptRules } from '@/api/users'

export function useMe() {
  return useQuery<User>({
    queryKey: ['user', 'me'],
    queryFn: getMe,
    staleTime: 0,
  })
}

export function useMyStats() {
  return useQuery<UserStats>({
    queryKey: ['user', 'stats'],
    queryFn: getMyStats,
    staleTime: 30_000,
  })
}

export function useReferralStats() {
  return useQuery<ReferralStats>({
    queryKey: ['user', 'referrals'],
    queryFn: getReferralStats,
    staleTime: 60_000,
  })
}

export function useNeedsAcceptRules() {
  return useQuery<{ needs_accept: boolean }>({
    queryKey: ['user', 'needs-accept-rules'],
    queryFn: checkNeedsAcceptRules,
    staleTime: 5 * 60_000,
  })
}
