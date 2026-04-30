import { api } from './client'
import type { Payout } from '@/lib/types'

export function getPayouts(): Promise<Payout[]> {
  return api.get('payouts/').json<Payout[]>()
}
