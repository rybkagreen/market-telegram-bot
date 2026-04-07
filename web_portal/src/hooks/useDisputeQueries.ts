import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { createDispute, getMyDisputes, getDisputeById, replyToDispute } from '@/api/disputes'
import type { DisputeDetailResponse, DisputeListResponse } from '@/lib/types'

export function useMyDisputes() {
  return useQuery<DisputeListResponse>({
    queryKey: ['disputes', 'my'],
    queryFn: getMyDisputes,
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
