import { api } from '@shared/api/client'
import type {
  DocumentUploadResponse,
  DocumentStatusResponse,
  PassportCompleteness,
} from '@/lib/types/documents'

export async function uploadDocument(
  file: File,
  documentType: string,
  passportPageGroup?: string,
) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_type', documentType)
  if (passportPageGroup) {
    formData.append('passport_page_group', passportPageGroup)
  }
  return api.post('legal-profile/documents/upload', { body: formData }).json<DocumentUploadResponse>()
}

export async function getUploadStatus(uploadId: number) {
  return api.get(`legal-profile/documents/${uploadId}/status`).json<DocumentStatusResponse>()
}

export async function getPassportCompleteness() {
  return api
    .get('legal-profile/documents/passport-completeness')
    .json<PassportCompleteness>()
}
