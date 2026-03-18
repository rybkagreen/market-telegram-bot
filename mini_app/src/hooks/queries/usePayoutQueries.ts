import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPayouts, createPayout } from '@/api/payouts'
import { useUiStore } from '@/stores/uiStore'

export const usePayouts = () =>
  useQuery({
    queryKey: ['payouts'],
    queryFn: getPayouts,
    staleTime: 60_000,
  })

export const useCreatePayout = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (data: { amount: number; payment_details: string }) => createPayout(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payouts'] })
      queryClient.invalidateQueries({ queryKey: ['user'] })
      addToast('success', 'Заявка на выплату создана')
    },
    onError: () => {
      addToast('error', 'Ошибка при создании заявки на выплату')
    },
  })
}
