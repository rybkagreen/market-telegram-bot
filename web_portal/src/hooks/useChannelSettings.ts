import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { checkChannel, addChannel, deleteChannel, activateChannel, getChannelSettings, updateChannelSettings } from '@/api/channels'

// ═══ Check channel ═══
export function useCheckChannel() {
  return useMutation({
    mutationFn: checkChannel,
  })
}

// ═══ Add channel ═══
export function useAddChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: addChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
    },
  })
}

// ═══ Delete channel ═══
export function useDeleteChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
    },
  })
}

// ═══ Activate channel ═══
export function useActivateChannel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: activateChannel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
    },
  })
}

// ═══ Channel settings ═══
export function useChannelSettings(id: number | null) {
  return useQuery({
    queryKey: ['channel-settings', id],
    queryFn: () => getChannelSettings(id!),
    enabled: !!id,
  })
}

export function useUpdateChannelSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      updateChannelSettings(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channel-settings'] })
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
    },
  })
}
