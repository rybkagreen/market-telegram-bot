import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Notification, Icon, ScreenHeader, Select } from '@shared/ui'
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
  { value: 'passport', label: 'Паспорт (2 фото)' },
  { value: 'tax_registration', label: 'Налоговая регистрация' },
  { value: 'self_employed_certificate', label: 'Справка о самозанятости' },
  { value: 'other', label: 'Другой документ' },
]

const PASSPORT_PAGES = [
  { value: 'main_pages', label: 'Страницы 2-3 (основная информация)' },
  { value: 'registration', label: 'Страница с пропиской' },
]

const ALLOWED_TYPES = [
  'image/jpeg',
  'image/jpg',
  'image/png',
  'image/webp',
  'image/heic',
  'application/pdf',
]
const MAX_SIZE = 10 * 1024 * 1024

function ProgressRing({ pct, size = 68 }: { pct: number; size?: number }) {
  const r = size / 2 - 7
  const c = 2 * Math.PI * r
  const cx = size / 2
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={cx} cy={cx} r={r} stroke="var(--color-harbor-elevated)" strokeWidth="6" fill="none" />
      <circle
        cx={cx}
        cy={cx}
        r={r}
        stroke="var(--color-accent)"
        strokeWidth="6"
        fill="none"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct / 100)}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 400ms ease' }}
      />
      <text
        x={cx}
        y={cx}
        transform={`rotate(90 ${cx} ${cx})`}
        textAnchor="middle"
        dominantBaseline="central"
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 14,
          fontWeight: 700,
          fill: 'var(--color-text-primary)',
        }}
      >
        {pct}%
      </text>
    </svg>
  )
}

export default function DocumentUpload() {
  const queryClient = useQueryClient()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [documentType, setDocumentType] = useState('inn_certificate')
  const [passportPage, setPassportPage] = useState('main_pages')
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)

  const uploadMutation = useUploadDocument()
  const { data: passportCompleteness } = usePassportCompleteness(documentType === 'passport')
  const { data: statusResult } = useUploadStatus(uploadResult?.upload_id ?? null)

  const polling =
    !!statusResult &&
    statusResult.status !== 'completed' &&
    statusResult.status !== 'failed' &&
    statusResult.status !== 'unreadable'

  const handleFileSelect = useCallback((file: File) => {
    setError(null)
    setUploadResult(null)

    if (!ALLOWED_TYPES.includes(file.type) && !file.name.toLowerCase().endsWith('.heic')) {
      setError('Неподдерживаемый формат. Допустимые: JPG, PNG, WEBP, HEIC, PDF')
      return
    }
    if (file.size > MAX_SIZE) {
      setError(`Файл слишком большой (${(file.size / 1024 / 1024).toFixed(1)} МБ). Максимум 10 МБ`)
      return
    }

    setSelectedFile(file)
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (e) => setPreview(e.target?.result as string)
      reader.readAsDataURL(file)
    } else {
      setPreview(null)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => setDragOver(false), [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragOver(false)
      const files = e.dataTransfer.files
      if (files.length > 0) handleFileSelect(files[0])
    },
    [handleFileSelect],
  )

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

  // Compute progress: how many document types have at least one uploaded (approximate)
  const docLabel =
    documentType === 'passport'
      ? passportPage === 'main_pages'
        ? 'Паспорт — стр. 2-3'
        : 'Паспорт — прописка'
      : DOCUMENT_TYPES.find((d) => d.value === documentType)?.label ?? documentType

  const passportProgress = documentType === 'passport' && passportCompleteness
    ? (passportCompleteness.main_pages_uploaded ? 50 : 0) +
      (passportCompleteness.registration_uploaded ? 50 : 0)
    : selectedFile
      ? 50
      : 0

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Документы', 'Загрузка']}
        title="Документы на верификацию"
        subtitle="Загрузите сканы — проверим в течение 24 часов"
        action={
          <Button variant="secondary" iconLeft="info">
            Требования
          </Button>
        }
      />

      <div className="bg-gradient-to-br from-harbor-card to-accent-muted border border-border rounded-xl p-5 mb-5 flex gap-[18px] items-center">
        <div className="flex-shrink-0">
          <ProgressRing pct={passportProgress} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-display text-base font-bold text-text-primary mb-0.5">
            {documentType === 'passport'
              ? `Паспорт: ${passportProgress}% загружено`
              : selectedFile
                ? 'Файл выбран — готов к загрузке'
                : 'Документ не выбран'}
          </div>
          <div className="text-[12.5px] text-text-secondary leading-[1.5]">
            После верификации вы сможете получать выплаты без удержания НДФЛ. Среднее время проверки — 3–6 часов
          </div>
        </div>
        {selectedFile && !uploadResult && (
          <Button variant="primary" iconLeft="upload" loading={uploadMutation.isPending} onClick={handleUpload}>
            Загрузить
          </Button>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <Notification type="danger">{error}</Notification>
        </div>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(0, 1.5fr) minmax(300px, 1fr)' }}>
        <div className="flex flex-col gap-4">
          {!uploadResult && (
            <SectionCard title="Загрузить документ" subtitle={docLabel}>
              <div className="mb-4">
                <div className="text-[11px] font-bold tracking-wider uppercase text-text-tertiary mb-2">
                  Тип документа
                </div>
                <Select
                  value={documentType}
                  onChange={setDocumentType}
                  options={DOCUMENT_TYPES}
                />
              </div>

              {documentType === 'passport' && passportCompleteness && (
                <div className="mb-4 p-3 bg-harbor-elevated rounded-lg">
                  <div className="text-sm font-medium text-text-primary mb-2">
                    Статус загрузки паспорта
                  </div>
                  <div className="flex items-center gap-3 text-sm mb-1">
                    <span
                      className={`flex items-center gap-1 ${passportCompleteness.main_pages_uploaded ? 'text-success' : 'text-text-tertiary'}`}
                    >
                      <Icon
                        name={passportCompleteness.main_pages_uploaded ? 'check' : 'pending'}
                        size={12}
                      />
                      Стр. 2-3
                    </span>
                    <span
                      className={`flex items-center gap-1 ${passportCompleteness.registration_uploaded ? 'text-success' : 'text-text-tertiary'}`}
                    >
                      <Icon
                        name={passportCompleteness.registration_uploaded ? 'check' : 'pending'}
                        size={12}
                      />
                      Прописка
                    </span>
                  </div>
                  {!passportCompleteness.is_complete && (
                    <div className="text-xs text-warning">Требуется загрузить оба фото</div>
                  )}
                </div>
              )}

              {documentType === 'passport' && (
                <div className="mb-4">
                  <div className="text-[11px] font-bold tracking-wider uppercase text-text-tertiary mb-2">
                    Какая страница
                  </div>
                  <div className="flex flex-col gap-2">
                    {PASSPORT_PAGES.map((page) => {
                      const isUploaded = passportCompleteness?.uploads.some(
                        (u) => u.page_group === page.value && u.status === 'completed',
                      )
                      const on = passportPage === page.value
                      return (
                        <label
                          key={page.value}
                          className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                            on
                              ? 'border-accent bg-accent-muted'
                              : 'border-border bg-harbor-elevated hover:border-border-active'
                          }`}
                        >
                          <input
                            type="radio"
                            name="passportPage"
                            value={page.value}
                            checked={on}
                            onChange={(e) => setPassportPage(e.target.value)}
                            className="sr-only"
                          />
                          <span
                            className={`w-[18px] h-[18px] rounded-full border-2 grid place-items-center flex-shrink-0 ${
                              on ? 'border-accent' : 'border-border-active'
                            }`}
                          >
                            {on && <span className="w-2 h-2 rounded-full bg-accent" />}
                          </span>
                          <span className="flex-1 text-sm text-text-primary">
                            {page.label}
                            {isUploaded && (
                              <span className="ml-2 text-xs text-success">(загружена)</span>
                            )}
                          </span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              )}

              <div
                className={`border-[1.5px] border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                  dragOver
                    ? 'border-accent bg-accent-muted'
                    : preview
                      ? 'border-accent bg-accent-muted/30'
                      : 'border-border bg-harbor-elevated hover:border-border-active'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => document.getElementById('doc-file-input')?.click()}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    document.getElementById('doc-file-input')?.click()
                  }
                }}
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
                  <div>
                    <div className="w-9 h-9 rounded-[9px] bg-harbor-card text-accent grid place-items-center mx-auto mb-2.5">
                      <Icon name="docs" size={16} />
                    </div>
                    <div className="text-[13px] font-semibold text-text-primary">{selectedFile.name}</div>
                    <div className="text-[11px] text-text-tertiary mt-1 font-mono tabular-nums">
                      {(selectedFile.size / 1024).toFixed(0)} КБ
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="w-9 h-9 rounded-[9px] bg-harbor-card text-accent grid place-items-center mx-auto mb-2.5">
                      <Icon name="upload" size={16} />
                    </div>
                    <div className="text-[12.5px] font-semibold text-text-primary">
                      Перетащите или выберите файл
                    </div>
                    <div className="text-[11px] text-text-tertiary mt-1">
                      JPG, PNG, WEBP, HEIC, PDF · до 10 МБ
                    </div>
                  </div>
                )}
              </div>

              <div className="mt-4 flex gap-2">
                <Button
                  variant="primary"
                  fullWidth
                  size="lg"
                  iconLeft="upload"
                  loading={uploadMutation.isPending}
                  disabled={!selectedFile}
                  onClick={handleUpload}
                >
                  {uploadMutation.isPending ? 'Загрузка…' : 'Загрузить и проверить'}
                </Button>
              </div>
            </SectionCard>
          )}

          {uploadResult && statusResult && (
            <SectionCard title="Результат проверки" subtitle={docLabel}>
              <div className="flex items-center gap-3 mb-4">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${
                    statusResult.status === 'completed'
                      ? 'bg-success-muted text-success'
                      : statusResult.status === 'processing' || statusResult.status === 'pending'
                        ? 'bg-warning-muted text-warning'
                        : statusResult.status === 'unreadable' || statusResult.status === 'failed'
                          ? 'bg-danger-muted text-danger'
                          : 'bg-harbor-elevated text-text-tertiary'
                  }`}
                >
                  {statusResult.status === 'completed'
                    ? 'Проверено'
                    : statusResult.status === 'processing'
                      ? 'Обработка…'
                      : statusResult.status === 'pending'
                        ? 'В очереди…'
                        : statusResult.status === 'unreadable'
                          ? 'Нечитаемо'
                          : statusResult.status === 'failed'
                            ? 'Ошибка'
                            : statusResult.status}
                </span>
                {polling && <span className="text-sm text-text-tertiary animate-pulse">Обновляется…</span>}
              </div>

              {statusResult.image_quality_score !== null && (
                <div className="mb-4">
                  <div className="text-sm text-text-secondary mb-1">Качество изображения</div>
                  <div className="w-full h-3 bg-harbor-elevated rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        statusResult.image_quality_score >= 0.7
                          ? 'bg-success'
                          : statusResult.image_quality_score >= 0.4
                            ? 'bg-warning'
                            : 'bg-danger'
                      }`}
                      style={{ width: `${statusResult.image_quality_score * 100}%` }}
                    />
                  </div>
                  <div className="text-xs text-text-tertiary mt-1">
                    {(statusResult.image_quality_score * 100).toFixed(0)}%
                    {statusResult.quality_issues && statusResult.quality_issues.length > 0 && (
                      <span className="text-danger"> — {statusResult.quality_issues.join(', ')}</span>
                    )}
                  </div>
                </div>
              )}

              {(statusResult.extracted_inn || statusResult.extracted_kpp || statusResult.extracted_ogrn) && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-text-primary mb-2">Извлечённые данные</div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {statusResult.extracted_inn && (
                      <div className="p-2 bg-harbor-elevated rounded">
                        <span className="text-text-tertiary">ИНН:</span>{' '}
                        <span className="text-text-primary font-mono">{statusResult.extracted_inn}</span>
                      </div>
                    )}
                    {statusResult.extracted_kpp && (
                      <div className="p-2 bg-harbor-elevated rounded">
                        <span className="text-text-tertiary">КПП:</span>{' '}
                        <span className="text-text-primary font-mono">{statusResult.extracted_kpp}</span>
                      </div>
                    )}
                    {statusResult.extracted_ogrn && (
                      <div className="p-2 bg-harbor-elevated rounded">
                        <span className="text-text-tertiary">ОГРН:</span>{' '}
                        <span className="text-text-primary font-mono">{statusResult.extracted_ogrn}</span>
                      </div>
                    )}
                    {statusResult.extracted_name && (
                      <div className="col-span-2 p-2 bg-harbor-elevated rounded">
                        <span className="text-text-tertiary">Название:</span>{' '}
                        <span className="text-text-primary">{statusResult.extracted_name}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {statusResult.validation_details && (
                <div className="mb-4">
                  <div className="text-sm font-medium text-text-primary mb-2">Сверка с профилем</div>
                  <div className="space-y-1">
                    {Object.entries(statusResult.validation_details.fields || {}).map(
                      ([field, data]: [string, DocumentValidationFieldDetail]) => (
                        <div
                          key={field}
                          className="flex items-center justify-between text-sm p-2 bg-harbor-elevated rounded"
                        >
                          <span className="text-text-secondary uppercase">{field}</span>
                          <span className={data.match ? 'text-success' : 'text-danger'}>
                            {data.match ? 'Совпадает' : data.reason}
                          </span>
                        </div>
                      ),
                    )}
                    {statusResult.validation_details.overall_confidence !== undefined && (
                      <div className="pt-2 border-t border-border flex items-center justify-between">
                        <span className="text-sm font-medium text-text-primary">Общее совпадение</span>
                        <span className="text-lg font-bold text-accent">
                          {(statusResult.validation_details.overall_confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {statusResult.error_message && (
                <Notification type="danger">{statusResult.error_message}</Notification>
              )}

              <Button variant="secondary" fullWidth iconLeft="upload" onClick={handleReset}>
                Загрузить другой документ
              </Button>
            </SectionCard>
          )}
        </div>

        <div className="flex flex-col gap-3.5">
          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="font-display text-[13px] font-semibold text-text-primary mb-3">
              Требования к документам
            </div>
            <ul className="list-none p-0 m-0 flex flex-col gap-2.5">
              {[
                'Читаемое изображение без бликов и теней',
                'Все углы документа видны',
                'Формат: JPG, PNG, WEBP, HEIC или PDF',
                'Размер файла — не более 10 МБ',
                'Для паспорта — 2 фото: стр. 2-3 + прописка',
              ].map((r) => (
                <li key={r} className="flex gap-2 text-[12.5px] text-text-secondary leading-[1.5]">
                  <span className="mt-0.5 w-4 h-4 rounded-full bg-accent-muted text-accent grid place-items-center flex-shrink-0">
                    <Icon name="check" size={10} strokeWidth={2.5} />
                  </span>
                  {r}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-harbor-elevated border border-dashed border-border rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-text-secondary leading-[1.5]">
            <Icon name="lock" size={13} className="text-accent mt-0.5 flex-shrink-0" />
            <span>
              Документы зашифрованы и доступны только арбитражу при разборе споров. Соответствие 152-ФЗ.
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section className="bg-harbor-card border border-border rounded-xl p-5">
      <div className="mb-4">
        <div className="font-display text-[13.5px] font-semibold text-text-primary">{title}</div>
        {subtitle && <div className="text-xs text-text-tertiary mt-[3px]">{subtitle}</div>}
      </div>
      {children}
    </section>
  )
}
