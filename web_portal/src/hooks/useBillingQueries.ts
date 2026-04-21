import { useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  initiateTopup,
  getBalance,
  getPlans,
  purchasePlan,
  getTransactionHistory,
  getTopupStatus,
  getFrozenBalance,
  type TopupStatus,
} from '@/api/billing'

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

const TOPUP_POLL_INTERVAL_MS = 3_000
const TOPUP_POLL_MAX_MS = 120_000

export function useTopupStatus(paymentId: string | null | undefined) {
  const queryClient = useQueryClient()
  const startedAtRef = useRef<number>(0)
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    if (!paymentId) return
    if (startedAtRef.current === 0) {
      startedAtRef.current = Date.now()
    }
    const elapsed = Date.now() - startedAtRef.current
    const remaining = Math.max(0, TOPUP_POLL_MAX_MS - elapsed)
    const handle = window.setTimeout(() => setTimedOut(true), remaining)
    return () => window.clearTimeout(handle)
  }, [paymentId])

  const query = useQuery<{ status: TopupStatus }>({
    queryKey: ['billing', 'topup-status', paymentId],
    enabled: Boolean(paymentId),
    queryFn: () => getTopupStatus(paymentId as string),
    refetchInterval: (q) => {
      const data = q.state.data
      if (data?.status === 'succeeded' || data?.status === 'canceled') return false
      if (Date.now() - startedAtRef.current >= TOPUP_POLL_MAX_MS) return false
      return TOPUP_POLL_INTERVAL_MS
    },
    staleTime: 0,
    gcTime: TOPUP_POLL_MAX_MS,
  })

  useEffect(() => {
    if (query.data?.status === 'succeeded') {
      queryClient.invalidateQueries({ queryKey: ['billing', 'balance'] })
      queryClient.invalidateQueries({ queryKey: ['billing', 'history'] })
      queryClient.invalidateQueries({ queryKey: ['user', 'me'] })
    }
  }, [query.data?.status, queryClient])

  return {
    ...query,
    status: query.data?.status,
    timedOut: timedOut && query.data?.status === 'pending',
  }
}

export function useTransactionHistory(page = 1, limit = 20) {
  return useQuery({
    queryKey: ['billing', 'history', page, limit],
    queryFn: () => getTransactionHistory(page, limit),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  })
}

export function useFrozenBalance() {
  return useQuery({
    queryKey: ['billing', 'frozen'],
    queryFn: getFrozenBalance,
    staleTime: 60_000,
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
