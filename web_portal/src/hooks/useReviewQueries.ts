import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { CreateReviewPayload } from '@/lib/types/misc'
import { createReview, getPlacementReviews } from '@/api/reviews'

export function useCreateReview() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: CreateReviewPayload) => createReview(payload),
    onSuccess: (_data, { placement_request_id }) => {
      queryClient.invalidateQueries({ queryKey: ['reviews', 'placement', placement_request_id] })
    },
  })
}

export function usePlacementReviews(placementRequestId: number | null | undefined) {
  return useQuery({
    queryKey: ['reviews', 'placement', placementRequestId],
    queryFn: () => getPlacementReviews(placementRequestId!),
    enabled: !!placementRequestId,
  })
}
