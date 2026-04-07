import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  searchChannels,
  createPlacement,
  getMyPlacements,
  getPlacement,
  updatePlacement,
  getPlacementRequest,
  startCampaign,
  cancelCampaign,
  duplicateCampaign,
} from '@/api/campaigns'
import { getCategories } from '@/api/categories'

// ═══ Categories ═══
export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 10 * 60 * 1000,
  })
}

// ═══ Available channels (by category) ═══
export function useAvailableChannels(category?: string) {
  return useQuery({
    queryKey: ['channels-available', category],
    queryFn: () => searchChannels({ category }),
    staleTime: 60 * 1000,
    enabled: true,
  })
}

// ═══ Placement by ID ═══
export function usePlacement(id: number | null | undefined, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ['placement', id],
    queryFn: () => getPlacement(id!),
    enabled: !!id,
    refetchInterval: options?.refetchInterval,
  })
}

// ═══ My placements (advertiser or owner list) ═══
export function useMyPlacements(status?: string, role?: 'advertiser' | 'owner') {
  return useQuery({
    queryKey: ['placements', status, role],
    queryFn: () => getMyPlacements({ status, role }),
    staleTime: 30_000,
  })
}

// ═══ Create placement (wizard submit) ═══
export function useCreatePlacement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createPlacement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}

// ═══ Update placement ═══
export function useUpdatePlacement() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      updatePlacement(id, data),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['placement', id] })
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}

// ═══ Placement request (legacy) ═══
export function usePlacementRequest(id: number | null) {
  return useQuery({
    queryKey: ['placement-request', id],
    queryFn: () => getPlacementRequest(id!),
    enabled: !!id,
  })
}

// ═══ Start campaign ═══
export function useStartCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => startCampaign(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['placement', id] })
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}

// ═══ Cancel campaign ═══
export function useCancelCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => cancelCampaign(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['placement', id] })
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}

// ═══ Duplicate campaign ═══
export function useDuplicateCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => duplicateCampaign(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}
