import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Card, Button, Notification } from '@shared/ui'
import {
  usePassportCompleteness,
  useUploadDocument,
  useUploadStatus,
} from '@/hooks/useDocumentQueries'
import type {
  DocumentUploadResponse,
  DocumentValidationFieldDetail,
} from '@/lib/types/documents'

const DOCUMENT_TYPES = [
  { value: 'inn_certificate', label: 'Свидетельство ИНН' },
  { value: 'ogrn_certificate', label: 'Свидетельство ОГРН/ОГРНИП' },
  { value: 'bank_details', label: 'Банковские реквизиты' },
  { value: 'passport', label: 'Паспорт (требуется 2 фото)' },
  { value: 'tax_registration', label: 'Налоговая регистрация' },
  { value: 'self_employed_certificate', label: 'Справка о самозанятости' },
  { value: 'other', label: 'Другой документ' },
]

// Passport page groups
const PASSPORT_PAGES = [
  { value: 'main_pages', label: '📄 Страницы 2-3 (основная информация)' },
  { value: 'registration', label: '📍 Страница с пропиской' },
]

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic', 'application/pdf']
const MAX_SIZE = 10 * 1024 * 1024 // 10 MB

export default function DocumentUpload() {
  const queryClient = useQueryClient()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('inn_certificate')
  const [passportPage, setPassportPage] = useState('main_pages')
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)

  const uploadMutation = useUploadDocument()
  const { data: passportCompleteness } = usePassportCompleteness(documentType === 'passport')
  const { data: statusResult } = useUploadStatus(uploadResult?.upload_id ?? null)

  const polling =
    !!statusResult &&
    statusResult.status !== 'completed' &&
    statusResult.status !== 'failed' &&
    statusResult.status !== 'unreadable'

  const handleDocumentTypeChange = (type: string) => {
    setDocumentType(type)
  }

  const handleFileSelect = useCallback((file: File) => {
    setError(null)
    setUploadResult(null)

    // Validate type
    if (!ALLOWED_TYPES.includes(file.type) && !file.name.toLowerCase().endsWith('.heic')) {
      setError('Неподдерживаемый формат. Допустимые: JPG, PNG, WEBP, HEIC, PDF')
      return
    }

    // Validate size
    if (file.size > MAX_SIZE) {
      setError(`Файл слишком большой (${(file.size / 1024 / 1024).toFixed(1)} МБ). Максимум 10 МБ`)
      return
    }

    setSelectedFile(file)

    // Create preview for images
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target?.result as string)
      reader.readAsDataURL(file)
    } else if (file.type === 'application/pdf') {
      setPreview(null) // Can't preview PDF easily
    }
  }, [])

  // Drag & drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    const files = e.dataTransfer.files
    if (files.length > 0) handleFileSelect(files[0])
  }, [handleFileSelect])

  const handleUpload = () => {
    if (!selectedFile) {
      setError('Выберите файл')
      return
    }

    setError(null)
    setUploadResult(null)
    uploadMutation.mutate(
      {
        file: selectedFile,
        documentType,
        passportPageGroup: documentType === 'passport' ? passportPage : undefined,
      },
      {
        onSuccess: (response) => {
          setUploadResult(response)
          if (documentType === 'passport') {
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: ['documents', 'passport-completeness'] })
            }, 2000)
          }
        },
        onError: () => setError('Ошибка загрузки. Попробуйте ещё раз.'),
      },
    )
  }

  const handleReset = () => {
    setSelectedFile(null)
    setUploadResult(null)
    setPreview(null)
    setError(null)
    setPassportPage('main_pages')
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">📄 Загрузка документов</h1>

      {error && <Notification type="danger">{error}</Notification>}

      {/* Upload form */}
      {!uploadResult && (
        <Card title="Загрузить документ для проверки">
          <div className="space-y-4">
            {/* Document type selector */}
            <div>
              <label className="block text-sm text-text-secondary mb-1">Тип документа</label>
              <select
                value={documentType}
                onChange={(e) => handleDocumentTypeChange(e.target.value)}
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary text-sm focus:border-accent focus:outline-none"
              >
                {DOCUMENT_TYPES.map((dt) => (
                  <option key={dt.value} value={dt.value}>{dt.label}</option>
                ))}
              </select>
            </div>

            {/* Passport page selector (only for passport) */}
            {documentType === 'passport' && (
              <>
                {/* Completeness status */}
                {passportCompleteness && (
                  <div className="p-3 bg-harbor-elevated rounded-lg space-y-2">
                    <p className="text-sm font-medium text-text-primary">📋 Статус загрузки паспорта:</p>
                    <div className="flex items-center gap-3 text-sm">
                      <span className={passportCompleteness.main_pages_uploaded ? 'text-success' : 'text-text-tertiary'}>
                        {passportCompleteness.main_pages_uploaded ? '✅ Стр. 2-3' : '⬜ Стр. 2-3'}
                      </span>
                      <span className={passportCompleteness.registration_uploaded ? 'text-success' : 'text-text-tertiary'}>
                        {passportCompleteness.registration_uploaded ? '✅ Прописка' : '⬜ Прописка'}
                      </span>
                    </div>
                    {passportCompleteness.is_complete && (
                      <p className="text-xs text-success font-medium">✅ Оба фото загружены</p>
                    )}
                    {!passportCompleteness.is_complete && (
                      <p className="text-xs text-warning">Требуется загрузить оба фото</p>
                    )}
                  </div>
                )}

                {/* Page selector */}
                <div>
                  <label className="block text-sm text-text-secondary mb-1">Какая страница паспорта?</label>
                  <div className="space-y-2">
                    {PASSPORT_PAGES.map((page) => {
                      const isUploaded = passportCompleteness?.uploads.some(
                        (u) => u.page_group === page.value && u.status === 'completed'
                      )
                      return (
                        <label
                          key={page.value}
                          className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                            ${passportPage === page.value
                              ? 'border-accent bg-accent-muted/10'
                              : 'border-border hover:border-accent/50'}`}
                        >
                          <input
                            type="radio"
                            name="passportPage"
                            value={page.value}
                            checked={passportPage === page.value}
                            onChange={(e) => setPassportPage(e.target.value)}
                            className="sr-only"
                          />
                          <div className="flex-1">
                            <span className="text-sm text-text-primary">{page.label}</span>
                            {isUploaded && (
                              <span className="ml-2 text-xs text-success">(уже загружена ✅)</span>
                            )}
                          </div>
                        </label>
                      )
                    })}
                  </div>
                </div>
              </>
            )}

            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
                ${preview ? 'border-accent bg-accent-muted/10' : 'border-border hover:border-accent/50'}`}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => document.getElementById('doc-file-input')?.click()}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') document.getElementById('doc-file-input')?.click() }}
              role="button"
              tabIndex={0}
              aria-label="Загрузить документ (нажмите или перетащите файл)"
            >
              <input
                id="doc-file-input"
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.heic,.pdf"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />

              {preview ? (
                <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-lg shadow-lg" />
              ) : selectedFile ? (
                <div className="space-y-2">
                  <p className="text-3xl">📎</p>
                  <p className="text-sm text-text-primary font-medium">{selectedFile.name}</p>
                  <p className="text-xs text-text-tertiary">{(selectedFile.size / 1024).toFixed(0)} КБ</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-3xl">📤</p>
                  <p className="text-sm text-text-secondary">
                    Перетащите файл сюда или <span className="text-accent">нажмите для выбора</span>
                  </p>
                  <p className="text-xs text-text-tertiary">JPG, PNG, WEBP, HEIC, PDF — до 10 МБ</p>
                </div>
              )}
            </div>

            {/* Upload button */}
            <Button
              variant="primary"
              fullWidth
              size="lg"
              loading={uploadMutation.isPending}
              disabled={!selectedFile || uploadMutation.isPending}
              onClick={handleUpload}
            >
              {uploadMutation.isPending ? '⏳ Загрузка...' : '📤 Загрузить и проверить'}
            </Button>
          </div>
        </Card>
      )}

      {/* Processing status */}
      {uploadResult && statusResult && (
        <Card title={`📋 Результат проверки: ${
          uploadResult.document_type === 'passport'
            ? `Паспорт (${statusResult.passport_page_group === 'main_pages' ? 'стр. 2-3' : 'прописка'})`
            : DOCUMENT_TYPES.find((d) => d.value === uploadResult.document_type)?.label
        }`}>
          <div className="space-y-4">
            {/* Status badge */}
            <div className="flex items-center gap-3">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                statusResult.status === 'completed' ? 'bg-success-muted text-success' :
                statusResult.status === 'processing' || statusResult.status === 'pending' ? 'bg-warning-muted text-warning' :
                statusResult.status === 'unreadable' ? 'bg-danger-muted text-danger' :
                'bg-harbor-elevated text-text-tertiary'
              }`}>
                {statusResult.status === 'completed' ? '✅ Проверено' :
                 statusResult.status === 'processing' ? '⏳ Обработка...' :
                 statusResult.status === 'pending' ? '⏳ В очереди...' :
                 statusResult.status === 'unreadable' ? '❌ Нечитаемо' :
                 statusResult.status === 'failed' ? '❌ Ошибка' : statusResult.status}
              </span>
              {polling && <span className="text-sm text-text-tertiary animate-pulse">Обновляется...</span>}
            </div>

            {/* Quality score */}
            {statusResult.image_quality_score !== null && (
              <div>
                <p className="text-sm text-text-secondary mb-1">Качество изображения</p>
                <div className="w-full h-3 bg-harbor-elevated rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      statusResult.image_quality_score >= 0.7 ? 'bg-success' :
                      statusResult.image_quality_score >= 0.4 ? 'bg-warning' : 'bg-danger'
                    }`}
                    style={{ width: `${statusResult.image_quality_score * 100}%` }}
                  />
                </div>
                <p className="text-xs text-text-tertiary mt-1">
                  {(statusResult.image_quality_score * 100).toFixed(0)}%
                  {statusResult.quality_issues && statusResult.quality_issues.length > 0 && (
                    <span className="text-danger"> — {statusResult.quality_issues.join(', ')}</span>
                  )}
                </p>
              </div>
            )}

            {/* OCR confidence */}
            {statusResult.ocr_confidence !== null && (
              <div>
                <p className="text-sm text-text-secondary mb-1">Уверенность распознавания</p>
                <p className="text-lg font-semibold text-text-primary">
                  {(statusResult.ocr_confidence * 100).toFixed(0)}%
                </p>
              </div>
            )}

            {/* Extracted data */}
            {(statusResult.extracted_inn || statusResult.extracted_kpp || statusResult.extracted_ogrn) && (
              <div>
                <p className="text-sm font-medium text-text-primary mb-2">Извлечённые данные:</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {statusResult.extracted_inn && (
                    <div className="p-2 bg-harbor-elevated rounded">
                      <span className="text-text-tertiary">ИНН:</span>
                      <span className="ml-1 text-text-primary font-mono">{statusResult.extracted_inn}</span>
                    </div>
                  )}
                  {statusResult.extracted_kpp && (
                    <div className="p-2 bg-harbor-elevated rounded">
                      <span className="text-text-tertiary">КПП:</span>
                      <span className="ml-1 text-text-primary font-mono">{statusResult.extracted_kpp}</span>
                    </div>
                  )}
                  {statusResult.extracted_ogrn && (
                    <div className="p-2 bg-harbor-elevated rounded">
                      <span className="text-text-tertiary">ОГРН:</span>
                      <span className="ml-1 text-text-primary font-mono">{statusResult.extracted_ogrn}</span>
                    </div>
                  )}
                  {statusResult.extracted_name && (
                    <div className="col-span-2 p-2 bg-harbor-elevated rounded">
                      <span className="text-text-tertiary">Название:</span>
                      <span className="ml-1 text-text-primary">{statusResult.extracted_name}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Validation results */}
            {statusResult.validation_details && (
              <div>
                <p className="text-sm font-medium text-text-primary mb-2">Сверка с профилем:</p>
                <div className="space-y-1">
                  {Object.entries(statusResult.validation_details.fields || {}).map(([field, data]: [string, DocumentValidationFieldDetail]) => (
                    <div key={field} className="flex items-center justify-between text-sm p-2 bg-harbor-elevated rounded">
                      <span className="text-text-secondary uppercase">{field}</span>
                      <span className={data.match ? 'text-success' : 'text-danger'}>
                        {data.match ? '✅ Совпадает' : `❌ ${data.reason}`}
                      </span>
                    </div>
                  ))}
                  {statusResult.validation_details.overall_confidence !== undefined && (
                    <div className="pt-2 border-t border-border">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-text-primary">Общее совпадение</span>
                        <span className="text-lg font-bold text-accent">
                          {(statusResult.validation_details.overall_confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error message */}
            {statusResult.error_message && (
              <Notification type="danger">{statusResult.error_message}</Notification>
            )}

            {/* Actions */}
            <Button variant="secondary" fullWidth onClick={handleReset}>
              📤 Загрузить другой документ
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
