import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyPayouts, createPayout, type Payout } from '@/api/payouts'

// ═══ My payouts ═══
export function useMyPayouts() {
  return useQuery<Payout[]>({
    queryKey: ['payouts', 'my'],
    queryFn: getMyPayouts,
    staleTime: 30_000,
  })
}

// ═══ Create payout ═══
export function useCreatePayout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPayout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payouts', 'my'] })
    },
  })
}
