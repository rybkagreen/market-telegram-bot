import { useState } from 'react'
import { Button, Notification } from '@/components/ui'
import { useRequestKep } from '@/hooks/useContractQueries'
import type { Contract, LegalStatus } from '@/lib/types'

interface KepWarningProps {
  contract: Contract
  legalStatus: LegalStatus
  onKepRequested?: () => void
}

const KEP_REQUIRED: LegalStatus[] = ['legal_entity', 'individual_entrepreneur']

export function KepWarning({ contract, legalStatus, onKepRequested }: KepWarningProps) {
  const [expanded, setExpanded] = useState(false)
  const [email, setEmail] = useState(contract.kep_request_email ?? '')
  const [done, setDone] = useState(false)
  const { mutate: requestKep, isPending } = useRequestKep()

  if (!KEP_REQUIRED.includes(legalStatus)) return null

  if (contract.kep_requested || done) {
    return (
      <Notification type="success">
        ✅ КЭП-версия запрошена. Ожидайте письма на{' '}
        <strong>{contract.kep_request_email ?? email}</strong> в течение 2 рабочих дней.
      </Notification>
    )
  }

  const warningText =
    legalStatus === 'legal_entity'
      ? '⚠️ Для принятия расходов к налоговому учёту и вычета НДС бухгалтерия потребует версию с КЭП через ЭДО. Вы можете подписать сейчас (ПЭП) и запросить КЭП-версию — мы направим в течение 2 рабочих дней.'
      : '⚠️ Для учёта рекламных расходов в налоговой базе рекомендуем запросить КЭП-версию.'

  const handleSend = () => {
    if (!email.trim()) return
    requestKep(
      { contractId: contract.id, email: email.trim() },
      {
        onSuccess: () => {
          setDone(true)
          onKepRequested?.()
        },
      },
    )
  }

  return (
    <div style={{ marginTop: 12 }}>
      <Notification type="warning">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>{warningText}</span>
      </Notification>

      <div style={{ marginTop: 8 }}>
        <button
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--rh-accent)',
            fontSize: 'var(--rh-text-sm, 14px)',
            cursor: 'pointer',
            padding: '4px 0',
          }}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? '▲ Скрыть форму' : '▼ Запросить КЭП-версию'}
        </button>

        {expanded && (
          <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <input
              type="email"
              placeholder="Email для получения КЭП-версии"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={{
                padding: '10px 12px',
                borderRadius: 8,
                border: '1px solid var(--rh-border)',
                fontSize: 'var(--rh-text-sm, 14px)',
                background: 'var(--rh-surface)',
                color: 'var(--rh-text)',
                width: '100%',
                boxSizing: 'border-box',
              }}
            />
            <Button
              variant="secondary"
              fullWidth
              disabled={isPending || !email.trim()}
              onClick={handleSend}
            >
              {isPending ? '⏳ Отправка...' : '📨 Отправить запрос'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
