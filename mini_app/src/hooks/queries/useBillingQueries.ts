import { useQuery, useMutation } from '@tanstack/react-query'
import { getPlans, createTopUp, getTopUpStatus } from '@/api/billing'
import { useUiStore } from '@/stores/uiStore'

export const usePlans = () =>
  useQuery({
    queryKey: ['billing', 'plans'],
    queryFn: getPlans,
    staleTime: 60 * 60_000,
  })

export const useCreateTopUp = () => {
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (desiredAmount: number) => createTopUp(desiredAmount),
    onError: () => {
      addToast('error', 'Ошибка при создании платежа')
    },
  })
}

export const useTopUpStatus = (id: string | null) =>
  useQuery({
    queryKey: ['billing', 'topup', id],
    queryFn: () => getTopUpStatus(id!),
    enabled: !!id,
    refetchInterval: 3000,
  })
