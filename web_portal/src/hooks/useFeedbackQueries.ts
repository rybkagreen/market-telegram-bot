import { useQuery } from '@tanstack/react-query'
import { getMyFeedback, getAdminDisputes, getAdminFeedback } from '@/api/feedback'
import type { UserFeedback, DisputeListResponse } from '@/lib/types'

export function useMyFeedback() {
  return useQuery<FeedbackListResponse>({
    queryKey: ['feedback', 'my'],
    queryFn: getMyFeedback,
    staleTime: 30_000,
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
  return useQuery<{ items: UserFeedback[]; total: number; limit: number; offset: number }>({
    queryKey: ['admin', 'feedback', params],
    queryFn: () => getAdminFeedback(params),
    staleTime: 30_000,
  })
}

export interface FeedbackListResponse {
  items: UserFeedback[]
  total: number
}
