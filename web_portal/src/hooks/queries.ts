import { useQuery } from '@tanstack/react-query'
import type { User, UserStats } from '@/lib/types'
import { getMe, getMyStats } from '@/api/users'
import { getMyContracts } from '@/api/legal'

export function useMe() {
  return useQuery<User>({
    queryKey: ['user', 'me'],
    queryFn: getMe,
    staleTime: 5 * 60 * 1000,
  })
}

export function useMyStats() {
  return useQuery<UserStats>({
    queryKey: ['user', 'stats'],
    queryFn: getMyStats,
    staleTime: 30_000,
  })
}

export function useContracts(type?: string) {
  return useQuery({
    queryKey: ['contracts', type],
    queryFn: () =>
      getMyContracts().then((data) => ({
        items: type ? data.items.filter((c) => c.contract_type === type) : data.items,
      })),
    staleTime: 30_000,
  })
}
