/**
 * React Query hooks for admin panel
 * 
 * Uses @tanstack/react-query for data fetching, caching, and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as adminApi from '@/api/admin'
import type {
  FeedbackListParams,
  DisputesListParams,
  UsersListParams,
  FeedbackRespondRequest,
  FeedbackStatusUpdateRequest,
  DisputeResolveRequest,
} from '@/api/admin'

// ============================================================
// Feedback Hooks
// ============================================================

export function useFeedbackList(params: FeedbackListParams) {
  return useQuery({
    queryKey: ['admin', 'feedback', params],
    queryFn: () => adminApi.getFeedbackList(params),
    staleTime: 30000, // 30 seconds
  })
}

export function useFeedbackById(id: number) {
  return useQuery({
    queryKey: ['admin', 'feedback', id],
    queryFn: () => adminApi.getFeedbackById(id),
    staleTime: 30000,
    enabled: id > 0,
  })
}

export function useRespondToFeedback() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: FeedbackRespondRequest }) =>
      adminApi.respondToFeedback(id, data),
    onSuccess: (data, { id }) => {
      // Invalidate feedback list and detail queries
      queryClient.invalidateQueries({ queryKey: ['admin', 'feedback'] })
      queryClient.setQueryData(['admin', 'feedback', id], data)
    },
  })
}

export function useUpdateFeedbackStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: FeedbackStatusUpdateRequest }) =>
      adminApi.updateFeedbackStatus(id, data),
    onSuccess: (data, { id }) => {
      // Invalidate feedback list and detail queries
      queryClient.invalidateQueries({ queryKey: ['admin', 'feedback'] })
      queryClient.setQueryData(['admin', 'feedback', id], data)
    },
  })
}

// ============================================================
// Disputes Hooks
// ============================================================

export function useDisputesList(params: DisputesListParams) {
  return useQuery({
    queryKey: ['admin', 'disputes', params],
    queryFn: () => adminApi.getDisputesList(params),
    staleTime: 30000,
  })
}

export function useDisputeById(id: number) {
  return useQuery({
    queryKey: ['admin', 'disputes', id],
    queryFn: () => adminApi.getDisputeById(id),
    staleTime: 30000,
    enabled: id > 0,
  })
}

export function useResolveDispute() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DisputeResolveRequest }) =>
      adminApi.resolveDispute(id, data),
    onSuccess: (data, { id }) => {
      // Invalidate disputes list and detail queries
      queryClient.invalidateQueries({ queryKey: ['admin', 'disputes'] })
      queryClient.setQueryData(['admin', 'disputes', id], data)
    },
  })
}

// ============================================================
// Stats Hooks
// ============================================================

export function usePlatformStats() {
  return useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: adminApi.getPlatformStats,
    staleTime: 60000, // 1 minute
    refetchInterval: 60000, // Refresh every minute
  })
}

// ============================================================
// Users Hooks
// ============================================================

export function useUsersList(params: UsersListParams) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => adminApi.getUsersList(params),
    staleTime: 30000,
  })
}

export function useUserById(id: number) {
  return useQuery({
    queryKey: ['admin', 'users', id],
    queryFn: () => adminApi.getUserById(id),
    staleTime: 30000,
    enabled: id > 0,
  })
}

export function useAddBalance() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: number; data: adminApi.BalanceTopUpRequest }) =>
      adminApi.addUserBalance(userId, data),
    onSuccess: (updated) => {
      queryClient.setQueryData(['admin', 'users', updated.id], updated)
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}
