import { api } from './client'
import type { LegalProfile, LegalProfileCreate, RequiredFields } from '@/lib/types'

export const legalProfileApi = {
  getMyProfile: () =>
    api.get('legal-profile/me').json<LegalProfile | null>(),

  createProfile: (data: LegalProfileCreate) =>
    api.post('legal-profile', { json: data }).json<LegalProfile>(),

  updateProfile: (data: Partial<LegalProfileCreate>) =>
    api.patch('legal-profile', { json: data }).json<LegalProfile>(),

  uploadScan: (scanType: string, fileId: string) =>
    api.post('legal-profile/scan', { json: { scan_type: scanType, file_id: fileId } }).json<{ success: boolean }>(),

  getRequiredFields: (legalStatus: string) =>
    api.get('legal-profile/required-fields', { searchParams: { legal_status: legalStatus } }).json<RequiredFields>(),

  validateInn: (inn: string) =>
    api.post('legal-profile/validate-inn', { json: { inn } }).json<{ valid: boolean; type: string }>(),

  skipLegalPrompt: () =>
    api.post('users/skip-legal-prompt').json<{ success: boolean }>(),
}
