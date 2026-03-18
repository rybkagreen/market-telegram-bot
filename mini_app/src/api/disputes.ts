import { api } from './client'
import type { Dispute, DisputeReason } from '@/lib/types'

export function getMyDisputes(): Promise<Dispute[]> {
  return api.get('disputes/').json<Dispute[]>()
}

export function createDispute(data: {
  placement_id: number
  reason: DisputeReason
  comment: string
}): Promise<Dispute> {
  return api.post('disputes/', { json: data }).json<Dispute>()
}

export function getDispute(id: number): Promise<Dispute> {
  return api.get(`disputes/${id}`).json<Dispute>()
}

export function replyToDispute(id: number, comment: string): Promise<Dispute> {
  return api.patch(`disputes/${id}`, { json: { owner_comment: comment } }).json<Dispute>()
}
