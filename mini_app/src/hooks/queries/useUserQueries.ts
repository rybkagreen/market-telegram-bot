import { useQuery } from '@tanstack/react-query'
import { getMe, getMyStats } from '@/api/users'

export const useMe = () =>
  useQuery({ queryKey: ['user', 'me'], queryFn: getMe, staleTime: 5 * 60_000 })

export const useMyStats = () =>
  useQuery({ queryKey: ['user', 'stats'], queryFn: getMyStats, staleTime: 5 * 60_000 })
