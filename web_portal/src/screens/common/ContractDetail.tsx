import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Skeleton, StatusPill } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import { KepWarning } from '@/components/contracts/KepWarning'
import { useContract, useSignContract } from '@/hooks/useContractQueries'

const TYPE_LABELS: Record<string, string> = {
  owner_service: '📋 Договор оказания услуг',
  advertiser_campaign: '📋 Договор на размещение рекламы',
  advertiser_framework: '📋 Рамочный договор рекламодателя',
  platform_rules: '📋 Правила платформы',
  privacy_policy: '🔒 Политика конфиденциальности',
  tax_agreement: '💰 Налоговое соглашение',
}

const STATUS_BADGE: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'default' }> = {
  draft: { label: 'Черновик', variant: 'default' },
  pending: { label: 'Ожидает подписи', variant: 'warning' },
  signed: { label: 'Подписан', variant: 'success' },
  expired: { label: 'Истёк', variant: 'danger' },
  cancelled: { label: 'Отменён', variant: 'default' },
}

const SIGN_BUTTON_LABEL: Record<string, string> = {
  individual: '✅ Подписать',
  self_employed: '✅ Подписать',
  individual_entrepreneur: '✅ Подписать (ПЭП)',
  legal_entity: '✅ Подписать (ПЭП — ознакомлен с ограничениями)',
}

const SUCCESS_MESSAGE: Record<string, string> = {
  individual: '✅ Договор подписан.',
  self_employed: '✅ Договор подписан. Не забудьте сформировать чек в «Мой налог» при получении выплаты.',
  individual_entrepreneur: '✅ Договор подписан. Сохраните PDF для налогового учёта.',
  legal_entity: '✅ Договор подписан. Для бухучёта рекомендуем запросить КЭП-версию.',
}

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : 0
  const [signed, setSigned] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: profile } = useMyLegalProfile()
  const legalStatus = profile?.legal_status ?? 'individual'

  const { data: contract, isLoading: loading, isError } = useContract(numId)
  const signMutation = useSignContract()

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-32" />
      </div>
    )
  }

  if (isError || !contract) {
    return <Notification type="danger">{error ?? 'Договор не найден'}</Notification>
  }

  const canSign = contract.contract_status === 'pending' || contract.contract_status === 'draft'
  const signLabel = SIGN_BUTTON_LABEL[legalStatus] ?? '✅ Подписать'
  const successMsg = SUCCESS_MESSAGE[legalStatus] ?? '✅ Договор подписан.'
  const badge = STATUS_BADGE[contract.contract_status] ?? STATUS_BADGE.draft
  const typeLabel = TYPE_LABELS[contract.contract_type] ?? contract.contract_type

  const handleSign = () => {
    signMutation.mutate(
      { id: contract.id, method: 'button_accept' },
      {
        onSuccess: () => setSigned(true),
        onError: () => setError('Ошибка при подписании'),
      },
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-bold text-text-primary">Договор</h1>
        <Button variant="secondary" size="sm" onClick={() => navigate('/contracts')}>← Назад</Button>
      </div>

      {/* Contract info */}
      <Card>
        <div className="flex items-start justify-between mb-3">
          <p className="text-sm font-medium text-text-primary">{typeLabel}</p>
          <StatusPill status={badge.variant}>{badge.label}</StatusPill>
        </div>
        {contract.signed_at && (
          <p className="text-xs text-text-tertiary mb-3">
            Подписан: {formatDateMSK(contract.signed_at)}
          </p>
        )}
        <div className="flex gap-2">
          {canSign && (
            <Button variant="primary" size="sm" loading={signMutation.isPending} onClick={handleSign}>
              {signMutation.isPending ? '⏳ Подписание...' : signLabel}
            </Button>
          )}
          {contract.pdf_url && (
            <Button variant="secondary" size="sm" onClick={() => window.open(contract.pdf_url!, '_blank')}>
              📥 Скачать PDF
            </Button>
          )}
        </div>
      </Card>

      {signed ? (
        <>
          <Notification type="success">{successMsg}</Notification>
          <KepWarning contract={contract} legalStatus={legalStatus} />
        </>
      ) : canSign ? (
        <KepWarning contract={contract} legalStatus={legalStatus} />
      ) : (
        contract.contract_status === 'signed' && <KepWarning contract={contract} legalStatus={legalStatus} />
      )}
    </div>
  )
}
