export interface DocumentUploadResponse {
  upload_id: number
  status: string
  file_type: string
  document_type: string
  passport_page_group?: string
}

export interface DocumentValidationFieldDetail {
  match: boolean
  reason?: string
}

export interface DocumentStatusResponse {
  upload_id: number
  status: string
  file_type: string
  document_type: string
  passport_page_group?: string
  image_quality_score: number | null
  quality_issues: string[] | null
  is_readable: boolean
  ocr_confidence: number | null
  extracted_inn: string | null
  extracted_kpp: string | null
  extracted_ogrn: string | null
  extracted_name: string | null
  validation_details: {
    fields?: Record<string, DocumentValidationFieldDetail>
    overall_confidence?: number
  } | null
  error_message: string | null
}

export interface PassportCompleteness {
  main_pages_uploaded: boolean
  registration_uploaded: boolean
  is_complete: boolean
  uploads: Array<{
    id: number
    page_group: string
    status: string
    quality_score: number | null
  }>
}
