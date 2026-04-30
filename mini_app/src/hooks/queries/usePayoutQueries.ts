import { useQuery } from '@tanstack/react-query'
import { getPayouts } from '@/api/payouts'

export const usePayouts = () =>
  useQuery({
    queryKey: ['payouts'],
    queryFn: getPayouts,
    staleTime: 60_000,
  })
