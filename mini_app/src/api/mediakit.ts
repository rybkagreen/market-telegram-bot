import { api } from './client'

export interface MediakitAdvertiserResponse {
  description: string | null
  audience_description: string | null
  logo_file_id: string | null
  theme_color: string | null
  avg_post_reach: number
  updated_at: string
}

/**
 * Fetch advertiser-readable mediakit for a channel.
 *
 * Backend: GET /api/channels/{channelId}/mediakit (B.5.1).
 * Returns 200 with body if mediakit is_published=true; 404 otherwise
 * (parity for not-published / not-exists / no-mediakit — no draft leak).
 * Caller hook translates 404 into "not available" empty state.
 */
export function getChannelMediakit(channelId: number): Promise<MediakitAdvertiserResponse> {
  return api.get(`channels/${channelId}/mediakit`).json<MediakitAdvertiserResponse>()
}
