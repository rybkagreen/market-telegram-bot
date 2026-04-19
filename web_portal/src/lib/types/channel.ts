export interface ChannelResponse {
  id: number
  telegram_id: number
  username: string
  title: string
  member_count: number
  category: string | null
  is_active: boolean
  rating: number
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
  category: string
  is_active: boolean
}
