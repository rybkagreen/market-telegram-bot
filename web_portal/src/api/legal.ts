import { api } from '@shared/api/client'
import type { LegalProfile, LegalProfileCreate, RequiredFields } from '@/lib/types/legal'
import type { Contract, ContractType } from '@/lib/types/contracts'

// ═══ Legal Profile ═══
// Backend prefix: /api/legal-profile (singular, no 's')
export async function getMyLegalProfile() {
  return api.get('legal-profile/me').json<LegalProfile>()
}

export async function createLegalProfile(data: LegalProfileCreate | Record<string, unknown>) {
  return api.post('legal-profile', { json: data }).json<LegalProfile>()
}

export async function updateLegalProfile(data: Record<string, unknown>) {
  return api.patch('legal-profile', { json: data }).json<LegalProfile>()
}

export async function skipLegalPrompt() {
  return api.post('users/skip-legal-prompt').json()
}

export async function validateInn(inn: string) {
  return api.post('legal-profile/validate-inn', { json: { inn } }).json<{ valid: boolean; legal_name?: string }>()
}

export async function getRequiredFields(legalStatus: string) {
  return api.get(`legal-profile/required-fields?legal_status=${legalStatus}`).json<RequiredFields>()
}

export async function validateEntity(data: {
  legal_status: string
  inn: string
  legal_name?: string
  kpp?: string
  ogrn?: string
  ogrnip?: string
}) {
  return api.post('legal-profile/validate-entity', { json: data }).json<{
    is_valid: boolean
    entity_type: string | null
    inn: string | null
    kpp: string | null
    ogrn: string | null
    status: string | null
    errors: { field: string; message: string }[]
    warnings: string[]
  }>()
}

// ═══ Contracts ═══
export async function getMyContracts() {
  return api.get('contracts').json<{ items: Contract[] }>()
}

export async function getContractById(id: number) {
  return api.get(`contracts/${id}`).json<Contract>()
}

export async function signContract(id: number, method: string) {
  return api.post(`contracts/${id}/sign`, { json: { method } }).json<Contract>()
}

export async function acceptRules() {
  return api.post('contracts/accept-rules').json()
}

export async function generateContract(contractType: ContractType, placementRequestId?: number) {
  return api
    .post('contracts/generate', { json: { contract_type: contractType, placement_request_id: placementRequestId } })
    .json<Contract>()
}

export async function requestKep(contractId: number, email: string) {
  return api.post(`contracts/${contractId}/request-kep`, { json: { email } }).json<Contract>()
}

export function getPdfUrl(id: number): string {
  return `contracts/${id}/pdf`
}
