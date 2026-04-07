import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyChannels, getChannelById, updateChannelCategory } from '@/api/channels'
import type { ChannelResponse } from '@/lib/types'

export function useMyChannels() {
  return useQuery<ChannelResponse[]>({
    queryKey: ['channels', 'my'],
    queryFn: getMyChannels,
    staleTime: 30_000,
  })
}

export function useChannelById(id: number | null) {
  return useQuery({
    queryKey: ['channels', id],
    queryFn: () => getChannelById(id!),
    enabled: !!id,
  })
}

export function useUpdateChannelCategory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, category }: { id: number; category: string }) =>
      updateChannelCategory(id, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
    },
  })
}
