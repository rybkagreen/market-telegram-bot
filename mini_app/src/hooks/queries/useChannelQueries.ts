import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMyChannels,
  getAvailableChannels,
  getChannelSettings,
  addChannel,
  checkChannel,
  updateChannelSettings,
  deleteChannel,
} from '@/api/channels'
import type { ChannelSettings } from '@/lib/types'
import { useUiStore } from '@/stores/uiStore'

export const useMyChannels = () =>
  useQuery({
    queryKey: ['channels', 'my'],
    queryFn: getMyChannels,
    staleTime: 2 * 60_000,
  })

export const useAvailableChannels = (category?: string) =>
  useQuery({
    queryKey: ['channels', 'available', category],
    queryFn: () => getAvailableChannels(category),
    staleTime: 2 * 60_000,
  })

export const useChannelSettings = (id: number | null) =>
  useQuery({
    queryKey: ['channels', id, 'settings'],
    queryFn: () => getChannelSettings(id!),
    enabled: !!id,
  })

export const useAddChannel = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (data: { username: string }) => addChannel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      addToast('success', 'Канал успешно добавлен')
    },
    onError: () => {
      addToast('error', 'Ошибка при добавлении канала')
    },
  })
}

export const useCheckChannel = () => {
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (username: string) => checkChannel(username),
    onError: () => {
      addToast('error', 'Ошибка при проверке канала')
    },
  })
}

export const useUpdateChannelSettings = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ChannelSettings> }) =>
      updateChannelSettings(id, data),
    onSuccess: (_data, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['channels', id] })
      addToast('success', 'Настройки канала сохранены')
    },
    onError: () => {
      addToast('error', 'Ошибка при сохранении настроек')
    },
  })
}

export const useDeleteChannel = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (id: number) => deleteChannel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      addToast('success', 'Канал удалён')
    },
    onError: () => {
      addToast('error', 'Ошибка при удалении канала')
    },
  })
}
