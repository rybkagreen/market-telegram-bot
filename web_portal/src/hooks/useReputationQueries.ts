import { useQuery } from '@tanstack/react-query'
import { getReputationHistory } from '@/api/reputation'

export function useReputationHistory(limit = 20, offset = 0) {
  return useQuery({
    queryKey: ['reputation', 'history', limit, offset],
    queryFn: () => getReputationHistory(limit, offset),
    staleTime: 30_000,
  })
}
