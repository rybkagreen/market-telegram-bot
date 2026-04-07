import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { initiateTopup, getBalance, getPlans, purchasePlan, getTransactionHistory } from '@/api/billing'

export function useBalance() {
  return useQuery({
    queryKey: ['billing', 'balance'],
    queryFn: getBalance,
    staleTime: 30_000,
  })
}

export function usePlans() {
  return useQuery({
    queryKey: ['billing', 'plans'],
    queryFn: getPlans,
    staleTime: 60_000,
  })
}

export function useInitiateTopup() {
  return useMutation({
    mutationFn: (desiredAmount: number) => initiateTopup(desiredAmount),
  })
}

export function useTransactionHistory(page = 1, limit = 20) {
  return useQuery({
    queryKey: ['billing', 'history', page, limit],
    queryFn: () => getTransactionHistory(page, limit),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })
}

export function usePurchasePlan() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (plan: string) => purchasePlan(plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user', 'me'] })
      queryClient.invalidateQueries({ queryKey: ['billing', 'plans'] })
    },
  })
}
