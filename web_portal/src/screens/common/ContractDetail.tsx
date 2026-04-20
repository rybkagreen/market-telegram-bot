import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import { KepWarning } from '@/components/contracts/KepWarning'
import { useContract, useSignContract } from '@/hooks/useContractQueries'

const TYPE_META: Record<string, { label: string; icon: IconName }> = {
  owner_service: { label: 'Договор оказания услуг', icon: 'contract' },
  advertiser_campaign: { label: 'Договор на размещение рекламы', icon: 'contract' },
  advertiser_framework: { label: 'Рамочный договор рекламодателя', icon: 'contract' },
  platform_rules: { label: 'Правила платформы', icon: 'docs' },
  privacy_policy: { label: 'Политика конфиденциальности', icon: 'lock' },
  tax_agreement: { label: 'Налоговое соглашение', icon: 'tax-doc' },
}

type Tone = 'success' | 'warning' | 'danger' | 'neutral'

const STATUS_META: Record<string, { label: string; tone: Tone; icon: IconName }> = {
  draft: { label: 'Черновик', tone: 'neutral', icon: 'draft' },
  pending: { label: 'Ожидает подписи', tone: 'warning', icon: 'hourglass' },
  signed: { label: 'Подписан', tone: 'success', icon: 'verified' },
  expired: { label: 'Истёк', tone: 'danger', icon: 'error' },
  cancelled: { label: 'Отменён', tone: 'neutral', icon: 'close' },
}

const toneClasses: Record<Tone, string> = {
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  danger: 'bg-danger-muted text-danger',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

const SIGN_BUTTON_LABEL: Record<string, string> = {
  individual: 'Подписать',
  self_employed: 'Подписать',
  individual_entrepreneur: 'Подписать (ПЭП)',
  legal_entity: 'Подписать (ПЭП — ознакомлен с ограничениями)',
}

const SUCCESS_MESSAGE: Record<string, string> = {
  individual: 'Договор подписан.',
  self_employed:
    'Договор подписан. Не забудьте сформировать чек в «Мой налог» при получении выплаты.',
  individual_entrepreneur: 'Договор подписан. Сохраните PDF для налогового учёта.',
  legal_entity: 'Договор подписан. Для бухучёта рекомендуем запросить КЭП-версию.',
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
      <div className="max-w-[900px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
      </div>
    )
  }

  if (isError || !contract) {
    return (
      <div className="max-w-[900px] mx-auto">
        <Notification type="danger">{error ?? 'Договор не найден'}</Notification>
      </div>
    )
  }

  const canSign = contract.contract_status === 'pending' || contract.contract_status === 'draft'
  const signLabel = SIGN_BUTTON_LABEL[legalStatus] ?? 'Подписать'
  const successMsg = SUCCESS_MESSAGE[legalStatus] ?? 'Договор подписан.'
  const status = STATUS_META[contract.contract_status] ?? STATUS_META.draft
  const type = TYPE_META[contract.contract_type] ?? {
    label: contract.contract_type,
    icon: 'contract' as IconName,
  }

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
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Документы', 'Договор']}
        title={type.label}
        subtitle={`№${contract.id}${contract.signed_at ? ` · подписан ${formatDateMSK(contract.signed_at)}` : ''}`}
        action={
          <Button variant="secondary" iconLeft="arrow-left" onClick={() => navigate('/contracts')}>
            К списку
          </Button>
        }
      />

      <div className="bg-harbor-card border border-border rounded-xl p-5 mb-5 relative overflow-hidden">
        <div
          className={`absolute top-0 left-0 right-0 h-[3px] ${contract.contract_status === 'signed' ? 'bg-gradient-to-r from-success to-accent' : 'bg-gradient-to-r from-accent to-accent-2'}`}
        />
        <div className="flex items-start gap-4 flex-wrap">
          <span
            className={`grid place-items-center w-12 h-12 rounded-[10px] flex-shrink-0 ${toneClasses[status.tone]}`}
          >
            <Icon name={type.icon} size={20} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-display text-[16px] font-semibold text-text-primary">
                {type.label}
              </span>
              <span
                className={`inline-flex items-center gap-1.5 text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded ${toneClasses[status.tone]}`}
              >
                <Icon name={status.icon} size={12} />
                {status.label}
              </span>
            </div>
            <div className="text-[12.5px] text-text-tertiary mt-1">№{contract.id}</div>
          </div>
          <div className="flex gap-2 flex-wrap">
            {canSign && (
              <Button
                variant="primary"
                iconLeft="check"
                loading={signMutation.isPending}
                onClick={handleSign}
              >
                {signLabel}
              </Button>
            )}
            {contract.pdf_url && (
              <Button
                variant="secondary"
                iconLeft="download"
                onClick={() => window.open(contract.pdf_url!, '_blank')}
              >
                Скачать PDF
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {signed && <Notification type="success">{successMsg}</Notification>}
        <KepWarning contract={contract} legalStatus={legalStatus} />
      </div>
    </div>
  )
}
