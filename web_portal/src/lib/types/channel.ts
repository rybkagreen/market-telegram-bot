export interface ChannelResponse {
  id: number
  telegram_id: number
  username: string
  title: string
  member_count: number
  last_er: number
  avg_views: number
  rating: number
  category: string | null
  is_active: boolean
  is_test: boolean
  owner_id: number
  created_at: string
}

export interface Channel {
  id: number
  telegram_id: number
  username: string
  title: string
  owner_id: number
  member_count: number
  rating: number
  category: string | null
  is_active: boolean
}
