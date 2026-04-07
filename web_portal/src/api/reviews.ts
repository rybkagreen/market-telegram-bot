import { api } from '@shared/api/client'
import type { ReviewResponse, PlacementReviewsResponse, CreateReviewPayload } from '@/lib/types/misc'

export async function createReview(payload: CreateReviewPayload) {
  return api.post('reviews', { json: payload }).json<ReviewResponse>()
}

export async function getPlacementReviews(placementRequestId: number) {
  return api.get(`reviews/placement/${placementRequestId}`).json<PlacementReviewsResponse>()
}
