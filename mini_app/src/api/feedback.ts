import { api } from './client'
import type { FeedbackCreateRequest, FeedbackListResponse, UserFeedback } from '@/lib/types'

/**
 * Create new feedback
 */
export function createFeedback(text: string): Promise<UserFeedback> {
  return api
    .post('feedback/', { json: { text } as FeedbackCreateRequest })
    .json<UserFeedback>()
}

/**
 * Get current user's feedback history
 */
export function getMyFeedback(): Promise<FeedbackListResponse> {
  return api.get('feedback/').json<FeedbackListResponse>()
}

/**
 * Get specific feedback by ID
 */
export function getFeedbackById(id: number): Promise<UserFeedback> {
  return api.get(`feedback/${id}`).json<UserFeedback>()
}
