import { useQuery } from '@tanstack/react-query'
import { getReputationHistory } from '@/api/reputation'

export function useReputationHistory(page = 1, limit = 20) {
  return useQuery({
    queryKey: ['reputation', 'history', page],
    queryFn: () => getReputationHistory(page, limit),
    staleTime: 30_000,
  })
}
