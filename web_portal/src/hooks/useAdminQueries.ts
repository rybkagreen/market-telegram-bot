import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getPlatformStats,
  getUsersList,
  getUserById,
  updateAdminUser,
  getAdminPayouts,
  approveAdminPayout,
  rejectAdminPayout,
  createPlatformCredit,
  createGamificationBonus,
} from '@/api/admin'

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
