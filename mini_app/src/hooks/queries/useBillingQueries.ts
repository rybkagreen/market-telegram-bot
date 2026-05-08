import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPlans, purchasePlan, getBillingHistory, getFeeConfig } from '@/api/billing'
import { useUiStore } from '@/stores/uiStore'

export const useBillingHistory = (page: number = 1) =>
  useQuery({
    queryKey: ['billing', 'history', page],
    queryFn: () => getBillingHistory(page, 20),
    staleTime: 30_000,
  })

export const usePlans = () =>
  useQuery({
    queryKey: ['billing', 'plans'],
    queryFn: getPlans,
    staleTime: 60 * 60_000,
  })

export const useFeeConfig = () =>
  useQuery({
    queryKey: ['billing', 'fee-config'],
    queryFn: getFeeConfig,
    staleTime: 5 * 60_000,
    gcTime: 30 * 60_000,
  })

export const usePurchasePlan = () => {
  const qc = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (plan: string) => purchasePlan(plan),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
      addToast('success', 'Тариф успешно изменён')
    },
    onError: (err: unknown) => {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 402) {
        addToast('error', 'Недостаточно средств. Пополните баланс.')
      } else if (status === 409) {
        addToast('error', 'Вы уже на этом тарифе')
      } else {
        addToast('error', 'Ошибка при смене тарифа')
      }
    },
  })
}
