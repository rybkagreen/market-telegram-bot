import { apiClient } from './client'

export interface CampaignItem {
  id: number
  title: string
  status: 'draft' | 'queued' | 'running' | 'done' | 'error' | 'paused' | 'cancelled'
  created_at: string
  sent_count: number
  target_count: number | null
  error_msg: string | null
}

export interface CampaignsResponse {
  items: CampaignItem[]
  total: number
  page: number
  pages: number
}

export interface CampaignStats {
  campaign_id: number
  title: string
  status: string
  total_logs: number
  sent: number
  failed: number
  skipped: number
  success_rate: number
  started_at: string | null
  finished_at: string | null
}

export interface CampaignStatsData {
  campaign_id: number
  title: string
  status: string
  total_logs: number
  sent: number
  failed: number
  skipped: number
  success_rate: number
  started_at: string | null
  finished_at: string | null
}

export const campaignsApi = {
  list: (params?: {
    status?: string
    page?: number
    limit?: number
  }): Promise<CampaignsResponse> =>
    apiClient.get('/campaigns/list', { params }).then(r => r.data),

  stats: (id: number): Promise<CampaignStatsData> =>
    apiClient.get(`/campaigns/${id}/stats`).then(r => r.data),

  delete: (id: number): Promise<void> =>
    apiClient.delete(`/campaigns/${id}`).then(() => undefined),

  duplicate: (id: number): Promise<{ id: number; title: string }> =>
    apiClient.post(`/campaigns/${id}/duplicate`).then(r => r.data),
}
