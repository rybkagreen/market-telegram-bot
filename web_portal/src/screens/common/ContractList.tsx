import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { Card, Button, Skeleton, EmptyState } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useContracts } from '@/hooks/useContractQueries'
import { api } from '@shared/api/client'
import * as Sentry from '@sentry/react'

const TYPE_LABELS: Record<string, string> = {
  owner_service: '📋 Договор оказания услуг (владелец)',
  advertiser_framework: '📋 Рамочный договор (рекламодатель)',
  tax_agreement: '💰 Налоговое соглашение',
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  draft: { label: 'Черновик', className: 'bg-harbor-elevated text-text-tertiary' },
  pending: { label: 'Ожидает подписания', className: 'bg-warning-muted text-warning' },
  signed: { label: 'Подписан', className: 'bg-success-muted text-success' },
  expired: { label: 'Истёк', className: 'bg-harbor-elevated text-text-tertiary' },
  cancelled: { label: 'Отменён', className: 'bg-danger-muted text-danger' },
}

export default function ContractList() {
  const navigate = useNavigate()
  const { data, isLoading } = useContracts()
  const [viewerOpen, setViewerOpen] = useState(false)
  const [viewerHtml, setViewerHtml] = useState('')
  const [viewerLoading, setViewerLoading] = useState(false)

  const openRulesViewer = async () => {
    setViewerOpen(true)
    setViewerLoading(true)
    try {
      const res = await api.get('contracts/platform-rules/text').json<{ html: string }>()
      setViewerHtml(DOMPurify.sanitize(res.html, { ALLOWED_TAGS: ['p','strong','em','ul','ol','li','h1','h2','h3','br','a','b','i','u'], ALLOWED_ATTR: ['href','class'] }))
    } catch (err) {
      Sentry.captureException(err)
      setViewerHtml('<p style="color:#e74c3c">Не удалось загрузить текст.</p>')
    } finally {
      setViewerLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    )
  }

  if (!data?.items.length) {
    return (
      <EmptyState icon="📄" title="Договоров пока нет" description="Договоры появятся после начала работы на платформе" />
    )
  }

  // Rules — one combined entry (platform_rules + privacy_policy)
  const hasRules = data.items.some(
    (c) => c.contract_type === 'platform_rules' || c.contract_type === 'privacy_policy',
  )

  // Other contracts (exclude rules)
  const otherContracts = data.items.filter(
    (c) => c.contract_type !== 'platform_rules' && c.contract_type !== 'privacy_policy',
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Мои договоры</h1>

      {/* Rules — single combined row */}
      {hasRules && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-text-primary">📋 Правила и Политика конфиденциальности</p>
              <span className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium bg-success-muted text-success">
                ✓ Принято
              </span>
            </div>
            <Button variant="secondary" size="sm" onClick={openRulesViewer}>
              📖 Читать
            </Button>
          </div>
        </Card>
      )}

      {/* Other contracts */}
      {otherContracts.length === 0 && !hasRules && (
        <EmptyState icon="📄" title="Договоров пока нет" />
      )}

      {otherContracts.map((contract) => {
        const badge = STATUS_BADGE[contract.status] ?? STATUS_BADGE.draft
        const typeLabel = TYPE_LABELS[contract.contract_type] ?? contract.contract_type
        const kepBadge = contract.kep_requested
          ? '🔏 КЭП запрошена'
          : null
        return (
          <Card key={contract.id} className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary">
                  {typeLabel}
                  {kepBadge && <span className="ml-2 text-xs text-warning">{kepBadge}</span>}
                </p>
                <p className="text-xs text-text-tertiary mt-1">
                  от {formatDateMSK(contract.created_at)}
                  {contract.signed_at && ` · подписан ${formatDateMSK(contract.signed_at)}`}
                </p>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${badge.className}`}>
                {badge.label}
              </span>
            </div>
            <div className="flex gap-2 mt-3">
              <Button variant="secondary" size="sm" onClick={() => navigate(`/contracts/${contract.id}`)}>
                {contract.status === 'signed' ? '👁️ Просмотр' : '✍️ Подписать'}
              </Button>
              {contract.pdf_url && (
                <Button variant="ghost" size="sm" onClick={() => window.open(contract.pdf_url!, '_blank')}>
                  📥 PDF
                </Button>
              )}
            </div>
          </Card>
        )
      })}

      {/* Rules viewer modal */}
      {viewerOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setViewerOpen(false)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setViewerOpen(false) } }}
          tabIndex={0}
          role="button"
          aria-label="Закрыть просмотр правил"
        >
          <div className="bg-harbor-card rounded-xl max-w-2xl w-full max-h-[80vh] flex flex-col mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-text-primary">Правила и Политика конфиденциальности</h3>
              <button className="text-text-tertiary hover:text-text-primary" onClick={() => setViewerOpen(false)}>✕</button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 prose prose-invert max-w-none">
              {viewerLoading ? (
                <p className="text-text-tertiary">Загрузка...</p>
              ) : (
                <div dangerouslySetInnerHTML={{ __html: viewerHtml }} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
