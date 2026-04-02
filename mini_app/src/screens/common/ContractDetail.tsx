import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Skeleton, Notification, Button } from '@/components/ui'
import { ContractCard } from '@/components/ContractCard'
import { KepWarning } from '@/components/KepWarning'
import { useContract, useSignContract } from '@/hooks/useContractQueries'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import type { LegalStatus } from '@/lib/types'

const SIGN_BUTTON_LABEL: Record<LegalStatus, string> = {
  individual: '✅ Подписать',
  self_employed: '✅ Подписать',
  individual_entrepreneur: '✅ Подписать (ПЭП)',
  legal_entity: '✅ Подписать (ПЭП — ознакомлен с ограничениями)',
}

const SUCCESS_MESSAGE: Record<LegalStatus, string> = {
  individual: '✅ Договор подписан.',
  self_employed: '✅ Договор подписан. Не забудьте сформировать чек в «Мой налог» при получении выплаты.',
  individual_entrepreneur: '✅ Договор подписан. Сохраните PDF для налогового учёта.',
  legal_entity: '✅ Договор подписан. Для бухучёта рекомендуем запросить КЭП-версию ниже.',
}

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>()
  const numId = id ? parseInt(id, 10) : 0
  const [signed, setSigned] = useState(false)

  const { data: contract, isLoading } = useContract(numId)
  const { data: profile } = useMyLegalProfile()
  const signMutation = useSignContract()

  const legalStatus: LegalStatus = (profile?.legal_status as LegalStatus) ?? 'individual'

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={120} />
        <Skeleton height={60} />
      </ScreenShell>
    )
  }

  if (!contract) {
    return (
      <ScreenShell>
        <Notification type="danger">Договор не найден</Notification>
      </ScreenShell>
    )
  }

  const canSign = contract.contract_status === 'pending' || contract.contract_status === 'draft'
  const signLabel = SIGN_BUTTON_LABEL[legalStatus] ?? '✅ Подписать'
  const successMsg = SUCCESS_MESSAGE[legalStatus] ?? '✅ Договор подписан.'

  const handleSign = () => {
    signMutation.mutate(
      { id: contract.id, method: 'button_accept' },
      { onSuccess: () => setSigned(true) },
    )
  }

  return (
    <ScreenShell>
      <ContractCard contract={contract} legalStatus={legalStatus} />

      {contract.pdf_url && (
        <a
          href={contract.pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: 'block',
            padding: '10px 16px',
            textAlign: 'center',
            color: 'var(--rh-accent)',
            fontSize: 'var(--rh-text-sm, 14px)',
            marginTop: 8,
          }}
        >
          📥 Скачать PDF
        </a>
      )}

      {signed ? (
        <>
          <Notification type="success">{successMsg}</Notification>
          <KepWarning contract={{ ...contract, contract_status: 'signed' }} legalStatus={legalStatus} />
        </>
      ) : canSign ? (
        <>
          <KepWarning contract={contract} legalStatus={legalStatus} />
          <div style={{ marginTop: 12 }}>
            <Button
              variant="primary"
              fullWidth
              disabled={signMutation.isPending}
              onClick={handleSign}
            >
              {signMutation.isPending ? '⏳ Подписание...' : signLabel}
            </Button>
          </div>
        </>
      ) : (
        <KepWarning contract={contract} legalStatus={legalStatus} />
      )}
    </ScreenShell>
  )
}
