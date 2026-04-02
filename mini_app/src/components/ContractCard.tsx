import { Card } from '@/components/ui/Card'
import { StatusPill } from '@/components/ui/StatusPill'
import { Button } from '@/components/ui/Button'
import type { Contract, ContractStatus } from '@/lib/types'

const CONTRACT_TYPE_LABELS: Record<string, string> = {
  owner_service: 'Договор оказания услуг',
  advertiser_campaign: 'Договор на размещение рекламы',
  advertiser_framework: 'Рамочный договор рекламодателя',
  platform_rules: 'Правила платформы',
  privacy_policy: 'Политика конфиденциальности',
  tax_agreement: 'Соглашение о налогах',
}

const KEP_NEEDS_STATUSES = ['legal_entity', 'individual_entrepreneur']

const STATUS_MAP: Record<ContractStatus, 'neutral' | 'warning' | 'success' | 'danger'> = {
  draft: 'neutral',
  pending: 'warning',
  signed: 'success',
  expired: 'danger',
  cancelled: 'neutral',
}

const STATUS_LABELS: Record<ContractStatus, string> = {
  draft: 'Черновик',
  pending: 'Ожидает подписи',
  signed: 'Подписан',
  expired: 'Истёк',
  cancelled: 'Отменён',
}

interface ContractCardProps {
  contract: Contract
  onSign?: () => void
  onView?: () => void
  legalStatus?: string
}

export function ContractCard({ contract, onSign, onView, legalStatus }: ContractCardProps) {
  const typeLabel = CONTRACT_TYPE_LABELS[contract.contract_type] ?? contract.contract_type
  const statusVariant = STATUS_MAP[contract.contract_status] ?? 'neutral'
  const statusLabel = STATUS_LABELS[contract.contract_status] ?? contract.contract_status
  const canSign = contract.contract_status === 'pending' || contract.contract_status === 'draft'

  const needsKep = legalStatus && KEP_NEEDS_STATUSES.includes(legalStatus)
  const kepBadge = contract.kep_requested
    ? <span style={{ fontSize: 'var(--rh-text-xs, 11px)', color: 'var(--rh-success, green)', marginLeft: 6 }}>🔏 КЭП запрошена</span>
    : needsKep && contract.contract_status === 'signed'
      ? <span style={{ fontSize: 'var(--rh-text-xs, 11px)', color: 'var(--rh-warning, orange)', marginLeft: 6 }}>⚠️ Нужна КЭП</span>
      : null

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
        <p style={{ margin: 0, fontWeight: 600, fontSize: 'var(--rh-text-sm, 14px)' }}>
          {typeLabel}
          {kepBadge}
        </p>
        <StatusPill status={statusVariant} size="sm">{statusLabel}</StatusPill>
      </div>
      {contract.signed_at && (
        <p style={{ margin: '0 0 8px', fontSize: 'var(--rh-text-xs, 12px)', color: 'var(--rh-text-muted)' }}>
          Подписан: {new Date(contract.signed_at).toLocaleDateString('ru-RU')}
        </p>
      )}
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        {onView && (
          <Button variant="secondary" size="sm" onClick={onView}>Посмотреть</Button>
        )}
        {canSign && onSign && (
          <Button variant="primary" size="sm" onClick={onSign}>Подписать</Button>
        )}
      </div>
    </Card>
  )
}
