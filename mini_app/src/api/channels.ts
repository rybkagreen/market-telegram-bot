import { api } from './client'
import type { Channel, ChannelSettings } from '@/lib/types'

export interface ChannelWithSettings extends Channel {
  settings: ChannelSettings
}

export function getMyChannels(): Promise<Channel[]> {
  return api.get('channels/').json<Channel[]>()
}

export function getAvailableChannels(category?: string): Promise<ChannelWithSettings[]> {
  return api
    .get('channels/available', { searchParams: category ? { category } : {} })
    .json<ChannelWithSettings[]>()
}

export function addChannel(data: { username: string }): Promise<Channel> {
  return api.post('channels/', { json: data }).json<Channel>()
}

export function checkChannel(
  username: string,
): Promise<{ valid: boolean; channel_info?: unknown; permissions?: unknown }> {
  return api
    .post('channels/check', { json: { username } })
    .json<{ valid: boolean; channel_info?: unknown; permissions?: unknown }>()
}

export function deleteChannel(id: number): Promise<void> {
  return api.delete(`channels/${id}`).json<void>()
}

export function getChannelSettings(id: number): Promise<ChannelSettings> {
  return api.get(`channels/${id}/settings`).json<ChannelSettings>()
}

export function updateChannelSettings(
  id: number,
  data: Partial<ChannelSettings>,
): Promise<ChannelSettings> {
  return api.patch(`channels/${id}/settings`, { json: data }).json<ChannelSettings>()
}
