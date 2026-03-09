import { apiClient } from './client'

export interface TopChannelItem {
  id: number
  title: string
  username: string | null
  subscribers: number
}

export interface CategoryStats {
  category: string
  total: number
  available_by_tariff: Record<string, number>
  top_channels: TopChannelItem[]
}

export interface TariffStatsItem {
  tariff: 'free' | 'starter' | 'pro' | 'business'
  label: string
  available: number
  percent_of_total: number
  premium_count: number
}

export interface DatabaseStats {
  total_channels: number
  total_categories: number
  added_last_7d: number
  last_updated: string
  tariff_stats: TariffStatsItem[]
  categories: CategoryStats[]
}

export interface ChannelPreviewItem {
  id: number
  title: string
  username: string | null
  subscribers: number
  topic: string | null
  rating: number | null
  is_premium: boolean
  is_accessible: boolean
}

export interface ChannelsPreview {
  total_accessible: number
  total_locked: number
  channels: ChannelPreviewItem[]
}

export interface ComparisonChannelItem {
  id: number
  username: string | null
  title: string | null
  member_count: number
  avg_views: number
  er: number
  post_frequency: number
  price_per_post: number
  price_per_1k_subscribers: number
  is_best: Record<string, boolean>
}

export interface ComparisonRecommendation {
  channel_id: number
  channel_name: string
  reason: string
}

export interface ComparisonResponse {
  channels: ComparisonChannelItem[]
  best_values: Record<string, number>
  recommendation: ComparisonRecommendation
}

export const channelsApi = {
  // Публичный — не требует токена
  stats: (): Promise<DatabaseStats> =>
    apiClient.get('/channels/stats').then(r => r.data),

  preview: (params?: { topic?: string; limit?: number }): Promise<ChannelsPreview> =>
    apiClient.get('/channels/preview', { params }).then(r => r.data),

  // Сравнение каналов
  compare: (channelIds: number[]): Promise<ComparisonResponse> =>
    apiClient.post('/channels/compare', { channel_ids: channelIds }),
}
