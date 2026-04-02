import { api } from './client'
import type { OrdRegistration } from '@/lib/types'

export const ordApi = {
  getStatus: (placementRequestId: number) =>
    api.get(`ord/${placementRequestId}`).json<OrdRegistration>(),

  register: (placementRequestId: number) =>
    api.post('ord/register', { json: { placement_request_id: placementRequestId } }).json<OrdRegistration>(),
}
