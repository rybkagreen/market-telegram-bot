import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'
import {
  getMyChannels,
  getAvailableChannels,
  getChannelSettings,
  addChannel,
  checkChannel,
  updateChannelSettings,
  updateChannelCategory,
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
    mutationFn: (data: { username: string; is_test?: boolean; category?: string }) => addChannel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
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
    onSuccess: (data) => {
      if (!data.valid) {
        if (data.missing_permissions.length > 0) {
          addToast(
            'error',
            `Боту не хватает прав: ${data.missing_permissions.join(', ')}`,
          )
        } else {
          addToast('error', 'Канал не найден или не является каналом')
        }
      } else if (data.is_already_added) {
        addToast('warning', 'Этот канал уже добавлен')
      } else {
        addToast('success', 'Канал успешно проверен')
      }
    },
    onError: (error: unknown) => {
      Sentry.captureException(error)
      let message = 'Ошибка при проверке канала'

      if (error && typeof error === 'object' && 'response' in error) {
        const typedError = error as { response?: { status?: number; data?: { detail?: string } } }
        if (typedError.response?.status === 400) {
          message = typedError.response?.data?.detail || 'Канал не найден'
        } else if (typedError.response?.status === 403) {
          message = 'Бот не является администратором канала'
        } else if (typedError.response?.status === 401) {
          message = 'Требуется авторизация'
        }
      }

      addToast('error', message)
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

export const useUpdateChannelCategory = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: ({ id, category }: { id: number; category: string }) =>
      updateChannelCategory(id, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
      queryClient.invalidateQueries({ queryKey: ['channels', 'available'] })
      addToast('success', 'Категория обновлена')
    },
    onError: () => {
      addToast('error', 'Ошибка при обновлении категории')
    },
  })
}

export const useDeleteChannel = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (id: number) => deleteChannel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels', 'my'] })
      addToast('success', 'Канал удалён')
    },
    onError: () => {
      addToast('error', 'Ошибка при удалении канала')
    },
  })
}
