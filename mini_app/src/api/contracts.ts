import { api } from './client'
import type { Contract, ContractType, SignatureMethod } from '@/lib/types'

export const contractsApi = {
  list: (params?: { type?: ContractType; status?: string }) =>
    api.get('contracts', { searchParams: params ?? {} }).json<{ items: Contract[]; total: number }>(),

  get: (id: number) =>
    api.get(`contracts/${id}`).json<Contract>(),

  generate: (contractType: ContractType, placementRequestId?: number) =>
    api.post('contracts/generate', { json: { contract_type: contractType, placement_request_id: placementRequestId } }).json<Contract>(),

  sign: (id: number, method: SignatureMethod, smsCode?: string) =>
    api.post(`contracts/${id}/sign`, { json: { signature_method: method, sms_code: smsCode } }).json<Contract>(),

  getPdfUrl: (id: number) => `contracts/${id}/pdf`,

  acceptRules: () =>
    api.post('contracts/accept-rules', { json: { accept_platform_rules: true, accept_privacy_policy: true } }).json<{ success: boolean }>(),

  requestKep: (contractId: number, email: string) =>
    api.post('contracts/request-kep', { json: { contract_id: contractId, email } }).json<{ success: boolean; message: string }>(),
}
