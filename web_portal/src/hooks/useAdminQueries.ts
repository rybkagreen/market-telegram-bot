import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPlatformStats,
  getUsersList,
  getUserById,
  updateAdminUser,
  topupUserBalance,
  getAdminPayouts,
  approveAdminPayout,
  rejectAdminPayout,
  createPlatformCredit,
  createGamificationBonus,
  getPlatformSettings,
  updatePlatformSettings,
  getTaxSummary,
  getKudirBlob,
} from '@/api/admin'
import type { PlatformSettingsPayload } from '@/lib/types/platform'

export function usePlatformStats() {
  return useQuery({
    queryKey: ['admin', 'platform-stats'],
    queryFn: getPlatformStats,
    staleTime: 60_000,
  })
}

export function useUsersList(params: {
  role?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => getUsersList(params),
    staleTime: 30_000,
  })
}

export function useUserById(userId: number) {
  return useQuery({
    queryKey: ['admin', 'user', userId],
    queryFn: () => getUserById(userId),
    enabled: !!userId,
  })
}

export function useUpdateAdminUser() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: number; data: { role?: string; plan?: string } }) =>
      updateAdminUser(userId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useTopupUserBalance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, amount, note }: { userId: number; amount: number; note?: string }) =>
      topupUserBalance(userId, { amount, note }),
    onSuccess: (_data, { userId }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'user', userId] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}

export function useAdminPayouts(params: {
  status?: string
  limit?: number
  offset?: number
}) {
  return useQuery({
    queryKey: ['admin', 'payouts', params],
    queryFn: () => getAdminPayouts(params),
    staleTime: 30_000,
  })
}

export function useApproveAdminPayout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payoutId: number) => approveAdminPayout(payoutId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'payouts'] })
    },
  })
}

export function useRejectAdminPayout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ payoutId, reason }: { payoutId: number; reason: string }) =>
      rejectAdminPayout(payoutId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'payouts'] })
    },
  })
}

export function useCreatePlatformCredit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: { user_id: number; amount: number; comment?: string }) =>
      createPlatformCredit(payload),
    onSuccess: (_data, { user_id }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'user', user_id] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'platform-stats'] })
    },
  })
}

export function usePlatformSettings(enabled: boolean = true) {
  return useQuery({
    queryKey: ['admin', 'platform-settings'],
    queryFn: getPlatformSettings,
    staleTime: 60_000,
    enabled,
  })
}

export function useUpdatePlatformSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: PlatformSettingsPayload) => updatePlatformSettings(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'platform-settings'] })
    },
  })
}

export function useTaxSummary(year: number, quarter: number, enabled: boolean = false) {
  return useQuery({
    queryKey: ['admin', 'tax-summary', year, quarter],
    queryFn: () => getTaxSummary(year, quarter),
    enabled,
    staleTime: 60_000,
  })
}

export async function downloadKudir(year: number, quarter: number, format: 'pdf' | 'csv') {
  const blob = await getKudirBlob(year, quarter, format)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `kudir_${year}_Q${quarter}.${format}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function useCreateGamificationBonus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: {
      user_id: number
      amount?: number
      xp_amount?: number
      comment?: string
    }) => createGamificationBonus(payload),
    onSuccess: (_data, { user_id }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'user', user_id] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'platform-stats'] })
    },
  })
}
