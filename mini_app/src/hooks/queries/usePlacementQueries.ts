import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMyPlacements,
  getPlacement,
  createPlacement,
  updatePlacement,
} from '@/api/placements'
import type { CreatePlacementData, UpdatePlacementData } from '@/api/placements'
import type { PlacementRequest, PlacementStatus } from '@/lib/types'
import { useUiStore } from '@/stores/uiStore'

interface GetPlacementsParams {
  status?: PlacementStatus
  channel_id?: number
  role?: 'advertiser' | 'owner'
}

export const useMyPlacements = (params?: GetPlacementsParams) =>
  useQuery({
    queryKey: ['placements', params],
    queryFn: () => getMyPlacements(params),
    staleTime: 30_000,
  })

export const usePlacement = (id: number | null, options?: { refetchInterval?: number }) =>
  useQuery({
    queryKey: ['placements', id],
    queryFn: () => getPlacement(id!),
    enabled: !!id,
    staleTime: 30_000,
    refetchInterval: options?.refetchInterval,
  })

export const useCreatePlacement = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (data: CreatePlacementData) => createPlacement(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['placements'] })
      addToast('success', 'Заявка на размещение создана')
    },
    onError: () => {
      addToast('error', 'Ошибка при создании заявки')
    },
  })
}

export const useUpdatePlacement = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdatePlacementData }) =>
      updatePlacement(id, data),
    onMutate: async ({ id, data }) => {
      await queryClient.cancelQueries({ queryKey: ['placements', id] })
      const previous = queryClient.getQueryData<PlacementRequest>(['placements', id])
      // Only optimistically update for non-action mutations (e.g., text edits)
      // Action mutations (pay/cancel) should NOT pollute cache with { action: '...' }
      if (previous && !('action' in data)) {
        queryClient.setQueryData<PlacementRequest>(['placements', id], {
          ...previous,
          ...data,
        })
      }
      return { previous, id }
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['placements', context.id], context.previous)
      }
      addToast('error', 'Ошибка при обновлении заявки')
    },
    onSettled: (_data, _err, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['placements'] })
      queryClient.invalidateQueries({ queryKey: ['placements', id] })
    },
    onSuccess: () => {
      addToast('success', 'Заявка обновлена')
    },
  })
}
