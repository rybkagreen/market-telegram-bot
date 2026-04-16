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
    mutationFn: (data: { gross_amount: number; requisites: string }) => createPayout(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payouts'] })
      queryClient.invalidateQueries({ queryKey: ['user'] })
      addToast('success', 'Заявка на выплату создана')
    },
    onError: (error: unknown) => {
      // GAP-01: Velocity check error handling
      const message = error instanceof Error ? error.message : String(error)
      const responseDetail =
        error && typeof error === 'object' && 'response' in error
          ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined
      const detail = responseDetail || message || ''
      if (detail.toLowerCase().includes('velocity') || detail.includes('80%') || detail.includes('превышен лимит')) {
        addToast('error', '⚠️ Превышен лимит вывода\n\nЗа последние 30 дней вы можете вывести не более 80% от суммы пополнений.')
      } else if (detail.toLowerCase().includes('cooldown') || detail.includes('24 часа')) {
        addToast('error', '⏱ Слишком частый вывод\n\nПовторите попытку через 24 часа после последней выплаты.')
      } else {
        addToast('error', 'Ошибка при создании заявки на выплату')
      }
    },
  })
}
