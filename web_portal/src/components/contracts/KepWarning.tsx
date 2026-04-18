import { useState } from 'react'
import { Button, Notification } from '@shared/ui'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { requestKep as apiRequestKep } from '@/api/legal'
import type { Contract } from '@/lib/types'

interface KepWarningProps {
  contract: Contract
  legalStatus: string
  onKepRequested?: () => void
}

const KEP_REQUIRED = ['legal_entity', 'individual_entrepreneur']

export function KepWarning({ contract, legalStatus, onKepRequested }: KepWarningProps) {
  const [expanded, setExpanded] = useState(false)
  const [email, setEmail] = useState(contract.kep_request_email ?? '')
  const [done, setDone] = useState(false)
  const [requesting, setRequesting] = useState(false)
  const qc = useQueryClient()

  const requestKep = useMutation({
    mutationFn: ({ contractId, email }: { contractId: number; email: string }) =>
      apiRequestKep(contractId, email),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['contracts'] })
    },
  })

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
    setRequesting(true)
    requestKep.mutate(
      { contractId: contract.id, email: email.trim() },
      {
        onSuccess: () => {
          setDone(true)
          onKepRequested?.()
          setRequesting(false)
        },
        onError: () => setRequesting(false),
      },
    )
  }

  return (
    <div className="mt-3">
      <Notification type="warning">
        <span className="text-sm">{warningText}</span>
      </Notification>

      <div className="mt-2">
        <button
          className="text-sm text-accent hover:text-accent-hover transition-colors cursor-pointer bg-transparent border-none p-0"
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? '▲ Скрыть форму' : '▼ Запросить КЭП-версию'}
        </button>

        {expanded && (
          <div className="mt-2 space-y-2">
            <input
              type="email"
              placeholder="Email для получения КЭП-версии"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-harbor-elevated border border-border rounded-md text-sm text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30"
            />
            <Button
              variant="secondary"
              fullWidth
              disabled={requesting || !email.trim()}
              onClick={handleSend}
            >
              {requesting ? '⏳ Отправка...' : '📨 Отправить запрос'}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
