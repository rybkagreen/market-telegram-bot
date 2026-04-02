import { useQuery } from '@tanstack/react-query'
import { getReferralStats } from '@/api/users'

export const useReferralStats = () =>
  useQuery({
    queryKey: ['referrals'],
    queryFn: getReferralStats,
    staleTime: 60_000, // 1 minute
    retry: 2,
  })
