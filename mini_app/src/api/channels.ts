import { api } from './client'
import type { Channel, ChannelSettings, ChannelCheckResponse } from '@/lib/types'

export interface ChannelWithSettings extends Channel {
  settings: ChannelSettings
}

export interface PreviewChannel {
  id: number
  title: string
  username: string
  subscribers: number
  topic: string
  rating: number
  is_premium: boolean
  is_accessible: boolean
}

export interface ChannelsPreviewResponse {
  total_accessible: number
  total_locked: number
  channels: PreviewChannel[]
}

export interface ChannelsPreviewParams {
  topic?: string
  limit?: number
  [key: string]: string | number | undefined
}

export interface ChannelCompareResponse {
  channels: Array<{
    id: number
    title: string
    username: string
    subscribers: number
    topic: string
    rating: number
    avg_views: number
    last_er: number
    price_per_post: number
  }>
}

export interface ChannelsStats {
  total_channels: number
  by_tariff: Record<string, number>
  avg_members: number
  total_members: number
}

export interface Subcategory {
  key: string
  name: string
  channel_count: number
}

export interface SubcategoriesResponse {
  parent_topic: string
  subcategories: Subcategory[]
}

/**
 * Сравнить каналы между собой
 */
export function compareChannels(channelIds: number[]): Promise<ChannelCompareResponse> {
  return api.post('channels/compare', { json: { channel_ids: channelIds } }).json<ChannelCompareResponse>()
}

/**
 * Получить публичную статистику базы каналов
 */
export function getChannelsStats(): Promise<ChannelsStats> {
  return api.get('channels/stats').json<ChannelsStats>()
}

/**
 * Получить подкатегории внутри темы
 */
export function getSubcategories(parentTopic: string): Promise<SubcategoriesResponse> {
  return api.get(`channels/subcategories/${parentTopic}`).json<SubcategoriesResponse>()
}

/**
 * Получить превью каналов для выбора при создании кампании
 */
export function getChannelsPreview(params?: ChannelsPreviewParams): Promise<ChannelsPreviewResponse> {
  return api.get('channels/preview', { searchParams: params ?? {} }).json<ChannelsPreviewResponse>()
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
