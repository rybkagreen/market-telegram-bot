import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createReview, getPlacementReviews } from '@/api/reviews'
import type { CreateReviewPayload } from '@/lib/types'

export const useGetPlacementReviews = (placementRequestId: number) =>
  useQuery({
    queryKey: ['reviews', placementRequestId],
    queryFn: () => getPlacementReviews(placementRequestId),
    enabled: !!placementRequestId,
    staleTime: 30_000,
  })

export const useCreateReview = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateReviewPayload) => createReview(payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['reviews', variables.placement_request_id] })
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}
