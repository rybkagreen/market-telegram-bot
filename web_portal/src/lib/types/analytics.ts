export interface ReputationScore {
  user_id: number
  advertiser_score: number
  owner_score: number
  is_advertiser_blocked: boolean
  is_owner_blocked: boolean
  advertiser_blocked_until: string | null
  owner_blocked_until: string | null
}

export interface ReputationHistoryItem {
  id: number
  user_id: number
  action: string
  delta: number
  score_before: number
  score_after: number
  role: string
  comment: string | null
  created_at: string
}

/** Backend GET /reputation/me/history returns a list directly; this
 *  interface is kept for optional admin paginated responses. */
export interface ReputationHistory {
  items: ReputationHistoryItem[]
  total: number
  page: number
  limit: number
}

export interface UserStats {
  reputation: ReputationScore
}

export interface PlatformStatsResponse {
  users: { total: number; active: number; admins: number }
  feedback: { total: number; new: number; in_progress: number; resolved: number; rejected: number }
  disputes: { total: number; open: number; owner_explained: number; resolved: number }
  placements: { total: number; pending: number; active: number; completed: number; cancelled: number }
  financial: {
    total_topups: string
    total_payouts: string
    net_balance: string
    escrow_reserved: string
    payout_reserved: string
    profit_accumulated: string
  }
}

export interface AdvertiserAnalyticsResponse {
  total_campaigns: number
  total_reach: number
  total_spent: string
  avg_ctr: number
  top_channels: Array<{
    channel: { id: number; username: string; title: string | null; member_count: number }
    reach: number
    ctr: number
  }>
  by_category: Array<{ category: string; count: number; percentage: number }>
}

export interface OwnerAnalyticsResponse {
  total_earned: string
  total_publications: number
  avg_rating: number
  channel_count: number
  by_channel: Array<{
    channel: { id: number; username: string; title: string; member_count: number }
    earned: string
    publications: number
  }>
  earnings_period: { today: string; week: string; month: string; total: string }
}
