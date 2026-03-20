import { api } from './client'
import type { Channel, ChannelSettings, ChannelCheckResponse } from '@/lib/types'

export interface ChannelWithSettings extends Channel {
  settings: ChannelSettings
}

/**
 * Получить мои каналы
 */
export function getMyChannels(): Promise<Channel[]> {
  return api.get('channels/').json<Channel[]>()
}

/**
 * Получить доступные каналы для размещения
 */
export function getAvailableChannels(category?: string): Promise<ChannelWithSettings[]> {
  return api
    .get('channels/available', { searchParams: category ? { category } : {} })
    .json<ChannelWithSettings[]>()
}

/**
 * Проверить канал перед добавлением
 * @param username - Username канала без @ или chat_id
 */
export function checkChannel(username: string): Promise<ChannelCheckResponse> {
  return api
    .post('channels/check', { 
      json: username.startsWith('-100') 
        ? { chat_id: parseInt(username) } 
        : { username: username.replace('@', '') } 
    })
    .json<ChannelCheckResponse>()
}

/**
 * Добавить новый канал
 */
export function addChannel(data: { 
  username: string
  is_test?: boolean  // Test mode (admin only)
}): Promise<Channel> {
  return api.post('channels/', { json: data }).json<Channel>()
}

/**
 * Удалить канал
 */
export function deleteChannel(id: number): Promise<void> {
  return api.delete(`channels/${id}`).json<void>()
}

/**
 * Получить настройки канала
 */
export function getChannelSettings(id: number): Promise<ChannelSettings> {
  return api.get('channel-settings/', { searchParams: { channel_id: id } }).json<ChannelSettings>()
}

/**
 * Обновить настройки канала
 */
export function updateChannelSettings(
  id: number,
  data: Partial<ChannelSettings>,
): Promise<ChannelSettings> {
  return api.patch('channel-settings/', { searchParams: { channel_id: id }, json: data }).json<ChannelSettings>()
}
