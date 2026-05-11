import { useQuery } from '@tanstack/react-query'

import { getChannelMediakit, type MediakitAdvertiserResponse } from '@/api/mediakit'

/**
 * Fetch published mediakit for a channel (advertiser view).
 *
 * 404 from backend manifests as query error; consumer checks `query.isError`
 * and renders empty state without leaking unpublished-draft existence.
 *
 * retry=false — 404 is a semantic terminal state, retries waste requests.
 */
export const useChannelMediakit = (channelId: number | null) =>
  useQuery<MediakitAdvertiserResponse>({
    queryKey: ['channels', channelId, 'mediakit'],
    queryFn: () => getChannelMediakit(channelId as number),
    enabled: channelId !== null,
    retry: false,
    staleTime: 2 * 60_000,
  })
