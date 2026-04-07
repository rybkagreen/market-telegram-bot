import { useQuery } from '@tanstack/react-query'
import { getAdvertiserAnalytics, getOwnerAnalytics } from '@/api/analytics'

export function useAdvertiserAnalytics() {
  return useQuery({
    queryKey: ['analytics', 'advertiser'],
    queryFn: getAdvertiserAnalytics,
    staleTime: 30_000,
  })
}

export function useOwnerAnalytics() {
  return useQuery({
    queryKey: ['analytics', 'owner'],
    queryFn: getOwnerAnalytics,
    staleTime: 30_000,
  })
}
