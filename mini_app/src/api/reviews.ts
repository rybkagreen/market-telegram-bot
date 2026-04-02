import { api } from './client'
import type { CreateReviewPayload, PlacementReviewsResponse, ReviewResponse } from '@/lib/types'

export function createReview(payload: CreateReviewPayload): Promise<ReviewResponse> {
  return api.post('reviews/', { json: payload }).json<ReviewResponse>()
}

export function getPlacementReviews(placementRequestId: number): Promise<PlacementReviewsResponse> {
  return api.get(`reviews/${placementRequestId}`).json<PlacementReviewsResponse>()
}
