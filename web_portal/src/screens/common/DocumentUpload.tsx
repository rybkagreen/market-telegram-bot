import { useState, useCallback } from 'react'
import { Card, Button, Notification } from '@shared/ui'
import { api } from '@shared/api/client'

const DOCUMENT_TYPES = [
  { value: 'inn_certificate', label: 'Свидетельство ИНН' },
  { value: 'ogrn_certificate', label: 'Свидетельство ОГРН/ОГРНИП' },
  { value: 'bank_details', label: 'Банковские реквизиты' },
  { value: 'passport', label: 'Паспорт' },
  { value: 'tax_registration', label: 'Налоговая регистрация' },
  { value: 'self_employed_certificate', label: 'Справка о самозанятости' },
  { value: 'other', label: 'Другой документ' },
]

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic', 'application/pdf']
const MAX_SIZE = 10 * 1024 * 1024 // 10 MB

interface UploadResult {
  upload_id: number
  status: string
  file_type: string
  document_type: string
}

interface StatusResult {
  upload_id: number
  status: string
  file_type: string
  document_type: string
  image_quality_score: number | null
  quality_issues: string[] | null
  is_readable: boolean
  ocr_confidence: number | null
  extracted_inn: string | null
  extracted_kpp: string | null
  extracted_ogrn: string | null
  extracted_name: string | null
  validation_details: Record<string, any> | null
  error_message: string | null
}

export default function DocumentUpload() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('inn_certificate')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [statusResult, setStatusResult] = useState<StatusResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)

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
  }, [])

  const handleFileSelect = (file: File) => {
    setError(null)
    setUploadResult(null)
    setStatusResult(null)

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
  }

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Выберите файл')
      return
    }

    setUploading(true)
    setError(null)
    setUploadResult(null)
    setStatusResult(null)

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      formData.append('document_type', documentType)

      const response = await api.post('legal-profile/documents/upload', {
        body: formData,
      }).json<UploadResult>()

      setUploadResult(response)
      setPolling(true)
      pollStatus(response.upload_id)
    } catch {
      setError('Ошибка загрузки. Попробуйте ещё раз.')
    } finally {
      setUploading(false)
    }
  }

  const pollStatus = async (uploadId: number) => {
    let attempts = 0
    const maxAttempts = 60 // 5 minutes at 5s interval

    const poll = async () => {
      if (attempts >= maxAttempts) {
        setPolling(false)
        setError('Обработка заняла слишком много времени. Попробуйте позже.')
        return
      }

      try {
        const result = await api.get(`legal-profile/documents/${uploadId}/status`).json<StatusResult>()
        setStatusResult(result)

        if (result.status === 'completed' || result.status === 'failed' || result.status === 'unreadable') {
          setPolling(false)
        } else {
          attempts++
          setTimeout(poll, 5000)
        }
      } catch {
        attempts++
        setTimeout(poll, 5000)
      }
    }

    poll()
  }

  const handleReset = () => {
    setSelectedFile(null)
    setUploadResult(null)
    setStatusResult(null)
    setPreview(null)
    setPolling(false)
    setError(null)
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
                onChange={(e) => setDocumentType(e.target.value)}
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary text-sm focus:border-accent focus:outline-none"
              >
                {DOCUMENT_TYPES.map((dt) => (
                  <option key={dt.value} value={dt.value}>{dt.label}</option>
                ))}
              </select>
            </div>

            {/* Drop zone */}
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors
                ${preview ? 'border-accent bg-accent-muted/10' : 'border-border hover:border-accent/50'}`}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => document.getElementById('doc-file-input')?.click()}
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
              loading={uploading}
              disabled={!selectedFile}
              onClick={handleUpload}
            >
              {uploading ? '⏳ Загрузка...' : '📤 Загрузить и проверить'}
            </Button>
          </div>
        </Card>
      )}

      {/* Processing status */}
      {uploadResult && statusResult && (
        <Card title={`📋 Результат проверки: ${DOCUMENT_TYPES.find((d) => d.value === uploadResult.document_type)?.label}`}>
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
                  {Object.entries(statusResult.validation_details.fields || {}).map(([field, data]: [string, any]) => (
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
