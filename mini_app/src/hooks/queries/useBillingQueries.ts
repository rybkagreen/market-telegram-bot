import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPlans, createTopUp, getTopUpStatus, purchasePlan, buyCredits } from '@/api/billing'
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

export const useBuyCredits = () => {
  const qc = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (amountRub: number) => buyCredits(amountRub),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
      addToast('success', `Зачислено ${data.credits_added} кредитов`)
    },
    onError: (err: unknown) => {
      const httpStatus = (err as { response?: { status?: number } })?.response?.status
      if (httpStatus === 402) {
        addToast('error', 'Недостаточно рублей на балансе')
      } else {
        addToast('error', 'Ошибка при покупке кредитов')
      }
    },
  })
}

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
        addToast('error', 'Недостаточно кредитов. Пополните баланс.')
      } else if (status === 409) {
        addToast('error', 'Вы уже на этом тарифе')
      } else {
        addToast('error', 'Ошибка при смене тарифа')
      }
    },
  })
}
