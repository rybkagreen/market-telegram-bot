import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listChannelVerifications,
  getChannelVerificationDetail,
  verifyChannelManually,
  rejectChannelVerification,
} from '@/api/admin_channel_verifications'
import type {
  ChannelVerificationDetailResponse,
  ChannelVerificationListResponse,
  ChannelVerificationRejectRequest,
  ChannelVerificationRejectResponse,
  ChannelVerificationStatus,
  ChannelVerificationVerifyRequest,
  ChannelVerificationVerifyResponse,
} from '@/api/admin_channel_verifications'

export function useAdminChannelVerifications(params?: {
  status?: ChannelVerificationStatus
  ownerId?: number
  limit?: number
  offset?: number
}) {
  return useQuery<ChannelVerificationListResponse>({
    queryKey: ['admin', 'channel-verifications', params],
    queryFn: () => listChannelVerifications(params),
    staleTime: 30_000,
  })
}

export function useAdminChannelVerificationDetail(channelId: number | null) {
  return useQuery<ChannelVerificationDetailResponse>({
    queryKey: ['admin', 'channel-verifications', channelId],
    queryFn: () => {
      if (channelId == null) throw new Error('channelId required')
      return getChannelVerificationDetail(channelId)
    },
    enabled: channelId != null,
  })
}

export function useVerifyChannelManually() {
  const queryClient = useQueryClient()
  return useMutation<
    ChannelVerificationVerifyResponse,
    Error,
    { channelId: number; body: ChannelVerificationVerifyRequest }
  >({
    mutationFn: ({ channelId, body }) => verifyChannelManually(channelId, body),
    onSuccess: (_data, { channelId }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'channel-verifications', channelId] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'channel-verifications'] })
    },
  })
}

export function useRejectChannelVerification() {
  const queryClient = useQueryClient()
  return useMutation<
    ChannelVerificationRejectResponse,
    Error,
    { channelId: number; body: ChannelVerificationRejectRequest }
  >({
    mutationFn: ({ channelId, body }) => rejectChannelVerification(channelId, body),
    onSuccess: (_data, { channelId }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'channel-verifications', channelId] })
      queryClient.invalidateQueries({ queryKey: ['admin', 'channel-verifications'] })
    },
  })
}
