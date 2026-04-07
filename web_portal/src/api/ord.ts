import { api } from '@shared/api/client'
import type { OrdRegistration } from '@/lib/types/misc'

export async function getOrdStatus(placementRequestId: number) {
  return api.get(`ord/${placementRequestId}`).json<OrdRegistration>()
}

export async function registerOrd(placementRequestId: number) {
  return api
    .post('ord/register', { json: { placement_request_id: placementRequestId } })
    .json<OrdRegistration>()
}
