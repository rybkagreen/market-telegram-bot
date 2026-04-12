import { api } from '@shared/api/client'
import type { ChannelResponse } from '@/lib/types'

export async function getMyChannels() {
  return api.get('channels').json<ChannelResponse[]>()
}

export async function getChannelById(id: number) {
  return api.get(`channels/${id}`).json<ChannelResponse>()
}

export async function updateChannelCategory(id: number, category: string) {
  return api.patch(`channels/${id}/category`, { json: { category } }).json<ChannelResponse>()
}

// ═══ Check channel (before adding) ═══
export async function checkChannel(identifier: string) {
  return api.post('channels/check', { json: { username: identifier } }).json<{
    valid: boolean
    is_already_added: boolean
    rules_valid: boolean
    rules_violations: string[]
    language_valid: boolean
    language_warnings: string[]
    channel: { title: string; username: string; member_count: number }
    bot_permissions: string[]
    category: string | null
  }>()
}

// ═══ Add channel ═══
export async function addChannel(data: { username: string; is_test?: boolean; category?: string }) {
  return api.post('channels', { json: data }).json<ChannelResponse>()
}

// ═══ Delete channel ═══
export async function deleteChannel(id: number): Promise<void> {
  await api.delete(`channels/${id}`).text()
}

// ═══ Activate channel ═══
export async function activateChannel(id: number) {
  return api.post(`channels/${id}/activate`).json<{
    id: number
    title: string
    username: string | null
    member_count: number
    category: string | null
    rating: number
    last_er: number
    avg_views: number
    is_active: boolean
  }>()
}

// ═══ Channel settings ═══
export async function getChannelSettings(id: number) {
  return api.get('channel-settings/', { searchParams: { channel_id: id } }).json<{
    price_per_post: string
    allow_format_post_24h: boolean
    allow_format_post_48h: boolean
    allow_format_post_7d: boolean
    allow_format_pin_24h: boolean
    allow_format_pin_48h: boolean
    publish_start_time: string | null
    publish_end_time: string | null
    break_start_time: string | null
    break_end_time: string | null
    max_posts_per_day: number
    auto_accept_enabled: boolean
  }>()
}

export async function updateChannelSettings(id: number, data: Record<string, unknown>) {
  return api.patch('channel-settings/', { searchParams: { channel_id: id }, json: data }).json<{
    channel_id: number
    price_per_post: string
    owner_payout: string
    publish_start_time: string
    publish_end_time: string
    break_start_time: string | null
    break_end_time: string | null
    max_posts_per_day: number
    allow_format_post_24h: boolean
    allow_format_post_48h: boolean
    allow_format_post_7d: boolean
    allow_format_pin_24h: boolean
    allow_format_pin_48h: boolean
    auto_accept_enabled: boolean
    updated_at: string
  }>()
}
