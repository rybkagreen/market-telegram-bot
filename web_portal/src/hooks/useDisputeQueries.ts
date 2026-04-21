import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  createDispute,
  getDisputeById,
  getDisputeByPlacement,
  getDisputeEvidence,
  getMyDisputes,
  replyToDispute,
  resolveDispute,
} from '@/api/disputes'
import type { DisputeDetailResponse, DisputeListResponse } from '@/lib/types'
import type { DisputeEvidenceResponse } from '@/api/disputes'

export function useMyDisputes(statusFilter = 'all', limit = 50, offset = 0) {
  return useQuery<DisputeListResponse>({
    queryKey: ['disputes', 'my', statusFilter, limit, offset],
    queryFn: () => getMyDisputes({ statusFilter, limit, offset }),
    staleTime: 30_000,
  })
}

export function useMyDisputeByPlacement(placementId: number | null) {
  return useQuery<DisputeDetailResponse | null>({
    queryKey: ['disputes', 'by-placement', placementId],
    queryFn: () => getDisputeByPlacement(placementId!),
    enabled: !!placementId,
    staleTime: 30_000,
  })
}

export function useDisputeById(id: number | null) {
  return useQuery<DisputeDetailResponse>({
    queryKey: ['disputes', id],
    queryFn: () => getDisputeById(id!),
    enabled: !!id,
  })
}

export function useDisputeEvidence(placementId: number | null) {
  return useQuery<DisputeEvidenceResponse>({
    queryKey: ['disputes', 'evidence', placementId],
    queryFn: () => getDisputeEvidence(placementId!),
    enabled: !!placementId,
    staleTime: 30_000,
  })
}

export function useCreateDispute() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: { placement_id: number; reason: string; comment: string }) =>
      createDispute(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['disputes'] })
    },
  })
}

export function useReplyToDispute() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, comment }: { id: number; comment: string }) =>
      replyToDispute(id, comment),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['disputes', id] })
    },
  })
}

export function useResolveDispute() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      resolution,
      adminComment,
      customSplitPercent,
    }: {
      id: number
      resolution: string
      adminComment?: string
      customSplitPercent?: number
    }) =>
      resolveDispute(id, resolution, adminComment, customSplitPercent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['disputes'] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'disputes'] })
    },
  })
}
