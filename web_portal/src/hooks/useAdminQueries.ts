import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPlatformStats, getUsersList, getUserById, updateAdminUser } from '@/api/admin'

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
