import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMyFeedback,
  createFeedback,
  getAdminDisputes,
  getAdminFeedback,
  getAdminFeedbackById,
  respondToFeedback,
  updateFeedbackStatus,
} from '@/api/feedback'
import type {
  UserFeedback,
  DisputeListResponse,
  FeedbackListResponse,
  FeedbackAdminListResponse,
  FeedbackAdminResponse,
  FeedbackRespondPayload,
  FeedbackStatusUpdatePayload,
} from '@/lib/types'

export function useMyFeedback() {
  return useQuery<FeedbackListResponse>({
    queryKey: ['feedback', 'my'],
    queryFn: getMyFeedback,
    staleTime: 30_000,
  })
}

export function useCreateFeedback() {
  const queryClient = useQueryClient()
  return useMutation<UserFeedback, Error, string>({
    mutationFn: (text) => createFeedback(text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback', 'my'] })
    },
  })
}

export function useAdminDisputes(params?: { status?: string; limit?: number; offset?: number }) {
  return useQuery<DisputeListResponse>({
    queryKey: ['admin', 'disputes', params],
    queryFn: () => getAdminDisputes(params),
    staleTime: 30_000,
  })
}

export function useAdminFeedback(params?: { status?: string; limit?: number; offset?: number }) {
  return useQuery<FeedbackAdminListResponse>({
    queryKey: ['admin', 'feedback', params],
    queryFn: () => getAdminFeedback(params),
    staleTime: 30_000,
  })
}

export function useAdminFeedbackById(feedbackId: number) {
  return useQuery<FeedbackAdminResponse>({
    queryKey: ['admin', 'feedback', feedbackId],
    queryFn: () => getAdminFeedbackById(feedbackId),
    enabled: !!feedbackId,
  })
}

export function useRespondToFeedback() {
  const queryClient = useQueryClient()
  return useMutation<
    FeedbackAdminResponse,
    Error,
    { feedbackId: number; payload: FeedbackRespondPayload }
  >({
    mutationFn: ({ feedbackId, payload }) => respondToFeedback(feedbackId, payload),
    onSuccess: (_data, { feedbackId }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feedback', feedbackId] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'feedback'] })
    },
  })
}

export function useUpdateFeedbackStatus() {
  const queryClient = useQueryClient()
  return useMutation<
    FeedbackAdminResponse,
    Error,
    { feedbackId: number; payload: FeedbackStatusUpdatePayload }
  >({
    mutationFn: ({ feedbackId, payload }) => updateFeedbackStatus(feedbackId, payload),
    onSuccess: (_data, { feedbackId }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'feedback', feedbackId] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'feedback'] })
    },
  })
}
