import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPlans, createTopUp, getTopUpStatus, purchasePlan, buyCredits, getBillingHistory, getFeeConfig } from '@/api/billing'
import { useUiStore } from '@/stores/uiStore'
import type { TopUpResponse } from '@/lib/types'

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

export const useCreateTopUp = () =>
  useMutation<TopUpResponse, unknown, number>({
    mutationFn: (desiredAmount: number) => createTopUp(desiredAmount),
  })

export const useTopUpStatus = (id: string | null) =>
  useQuery({
    queryKey: ['billing', 'topup', id],
    queryFn: () => getTopUpStatus(id!),
    enabled: !!id,
    refetchInterval: 3000,
  })

export const useBuyCredits = () => {
  const qc = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (amountRub: number) => buyCredits(amountRub),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
      addToast('success', `Оплачено ${data.amount_rub} ₽`)
    },
    onError: (err: unknown) => {
      const httpStatus = (err as { response?: { status?: number } })?.response?.status
      if (httpStatus === 402) {
        addToast('error', 'Недостаточно средств на балансе')
      } else {
        addToast('error', 'Ошибка при оплате тарифа')
      }
    },
  })
}

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
