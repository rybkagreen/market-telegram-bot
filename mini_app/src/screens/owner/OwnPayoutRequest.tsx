import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, AmountChips, FeeBreakdown, Notification } from '@/components/ui'
import { ContractCard } from '@/components/ContractCard'
import { KepWarning } from '@/components/KepWarning'
import { TaxBreakdown } from '@/components/TaxBreakdown'
import { MIN_WITHDRAWAL } from '@/lib/constants'
import { formatCurrency, calcWithdrawalFee } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { useMe, useCreatePayout } from '@/hooks/queries'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import { useContracts, useSignContract } from '@/hooks/useContractQueries'
import type { LegalStatus } from '@/lib/types'
import styles from './OwnPayoutRequest.module.css'

const PRESET_AMOUNTS = [1000, 3000, 5000, 10000]

export default function OwnPayoutRequest() {
  const navigate = useNavigate()
  const haptic = useHaptic()

  const { data: me } = useMe()
  const { mutate: createPayout, isPending } = useCreatePayout()
  const { data: legalProfile } = useMyLegalProfile()
  const { data: ownerContracts } = useContracts('owner_service')
  const { mutate: signContract, isPending: signing } = useSignContract()

  const legalStatus = (legalProfile?.legal_status ?? 'individual') as LegalStatus
  const ownerContract = ownerContracts?.items.find((c) => c.contract_status === 'signed') ?? null
  const ownerContractPending = ownerContracts?.items.find(
    (c) => c.contract_status === 'pending' || c.contract_status === 'draft',
  ) ?? null
  const contractReady = !!ownerContract

  const earnedRub = parseFloat(me?.earned_rub ?? '0')
  const [amount, setAmount] = useState(0)
  const [paymentDetails, setPaymentDetails] = useState('')

  const fee = calcWithdrawalFee(amount)

  const isValid =
    contractReady &&
    amount >= MIN_WITHDRAWAL &&
    amount <= earnedRub &&
    paymentDetails.length >= 5

  const handleSubmit = () => {
    haptic.success()
    createPayout(
      { amount, payment_details: paymentDetails },
      { onSuccess: () => { navigate('/own/payouts') } },
    )
  }

  if (me && !me.legal_status_completed) {
    return (
      <ScreenShell>
        <Notification type="warning">
          ⚠️ Для запроса выплаты необходимо заполнить юридический профиль.
        </Notification>
        <Button variant="primary" fullWidth onClick={() => navigate('/legal-profile')}>
          Заполнить профиль
        </Button>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell>
      {/* Owner service contract section */}
      {ownerContract ? (
        <div className={styles.contractSection}>
          <p className={styles.contractSigned}>✅ Договор оказания услуг подписан</p>
          <ContractCard contract={ownerContract} legalStatus={legalStatus} onView={() => navigate(`/contracts/${ownerContract.id}`)} />
          <KepWarning contract={ownerContract} legalStatus={legalStatus} />
        </div>
      ) : ownerContractPending ? (
        <div className={styles.contractSection}>
          <Notification type="warning">
            Для получения выплаты необходимо подписать договор оказания услуг.
          </Notification>
          <ContractCard
            contract={ownerContractPending}
            legalStatus={legalStatus}
            onSign={() => signContract({ id: ownerContractPending.id, method: 'button_accept' })}
          />
          <KepWarning contract={ownerContractPending} legalStatus={legalStatus} />
          {signing && <Notification type="info">⏳ Подписание...</Notification>}
        </div>
      ) : null}
      <Card title="Доступно к выводу">
        <p className={styles.available}>{formatCurrency(earnedRub)}</p>
      </Card>

      <label className={styles.label}>Сумма вывода</label>

      <AmountChips
        amounts={PRESET_AMOUNTS}
        selected={PRESET_AMOUNTS.includes(amount) ? amount : undefined}
        onSelect={setAmount}
      />

      <button className={styles.allBtn} onClick={() => setAmount(earnedRub)}>
        Вывести всё ({formatCurrency(earnedRub)})
      </button>

      <input
        className={styles.input}
        type="number"
        placeholder="Введите сумму"
        value={amount === 0 ? '' : String(amount)}
        onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
      />

      {amount > 0 && (
        <FeeBreakdown
          rows={[
            { label: 'Запрашиваемая сумма', value: formatCurrency(fee.gross) },
            { label: 'Комиссия за перевод (1,5%)', value: `−${formatCurrency(fee.fee)}`, dim: true },
          ]}
          total={{ label: 'Будет переведено', value: formatCurrency(fee.net) }}
        />
      )}

      {/* GAP-04: USN 6% tax hint */}
      <p className={styles.usnNote}>
        ℹ️ Платформа учитывает налог УСН 6% при расчёте выплат
      </p>

      <label className={styles.label}>Реквизиты (номер карты / СБП)</label>
      <input
        className={styles.input}
        type="text"
        placeholder="Номер карты или телефон для СБП"
        value={paymentDetails}
        onChange={(e) => setPaymentDetails(e.target.value)}
      />

      <Notification type="info">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          ⏱ Обработка: до 24 часов · 09:00–22:00 МСК
        </span>
      </Notification>

      {amount > 0 && legalProfile && (
        <TaxBreakdown
          grossAmount={amount}
          legalStatus={legalProfile.legal_status}
          taxRegime={legalProfile.tax_regime ?? undefined}
        />
      )}

      <Button fullWidth disabled={!isValid || isPending} onClick={handleSubmit}>
        {isPending ? '⏳ Отправка...' : '💸 Запросить вывод'}
      </Button>
    </ScreenShell>
  )
}
