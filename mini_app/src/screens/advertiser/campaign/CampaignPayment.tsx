import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, FeeBreakdown, Button, Skeleton } from '@/components/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import { useContracts } from '@/hooks/useContractQueries'
import styles from './CampaignPayment.module.css'

export default function CampaignPayment() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)
  const { mutate: updatePlacement, isPending } = useUpdatePlacement()
  const { data: contractsList, isLoading: contractsLoading } = useContracts('advertiser_framework')

  // Check for signed framework contract — redirect to sign it if missing (skip for test campaigns)
  useEffect(() => {
    if (!contractsLoading && contractsList && placement && !placement.is_test) {
      const hasSigned = contractsList.items.some(
        (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
      )
      if (!hasSigned) {
        navigate(`/contracts/framework?returnTo=/adv/campaigns/${numId}/payment`, { replace: true })
      }
    }
  }, [contractsList, contractsLoading, placement, navigate, numId])

  const frameworkContract = contractsList?.items.find(
    (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
  )

  if (isLoading || (contractsLoading && !placement?.is_test)) {
    return (
      <ScreenShell>
        <Skeleton height={80} />
        <Skeleton height={150} />
      </ScreenShell>
    )
  }

  if (!placement) {
    return (
      <ScreenShell>
        <Notification type="danger">Заявка не найдена</Notification>
      </ScreenShell>
    )
  }

  const formatInfo = PUBLICATION_FORMATS[placement.publication_format]
  const price = placement.final_price ?? placement.proposed_price

  const frameworkRef = frameworkContract
    ? `рамочному договору №${frameworkContract.id} от ${new Date(frameworkContract.signed_at!).toLocaleDateString('ru-RU')}`
    : 'рамочному договору'

  return (
    <ScreenShell>
      <Notification type="success">✅ Владелец принял условия!</Notification>

      <p className={styles.sectionTitle}>К оплате</p>

      <FeeBreakdown
        rows={[
          {
            label: `@${placement.channel?.username ?? `#${placement.channel_id}`} · ${formatInfo.name}`,
            value: formatCurrency(price),
          },
          {
            label: 'Комиссия платформы (15%)',
            value: 'включена',
            dim: true,
          },
        ]}
        total={{ label: 'Итого', value: formatCurrency(price) }}
      />

      <Notification type="info">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          ⏱ Действует до {formatDateTime(placement.expires_at)} (24 ч)
        </span>
      </Notification>

      <Notification type="info">
        <span style={{ fontSize: 'var(--rh-text-xs)' }}>
          📄 Нажимая «Оплатить», вы подтверждаете размещение рекламы в выбранных каналах согласно{' '}
          {frameworkRef}.
        </span>
      </Notification>

      <div className={styles.buttons}>
        <Button variant="secondary" fullWidth onClick={() => navigate('/adv')}>
          ← В меню рекламодателя
        </Button>

        <Button
          variant="primary"
          fullWidth
          disabled={isPending}
          onClick={() => {
            haptic.success()
            updatePlacement(
              { id: placement.id, data: { action: 'pay' } },
              { onSuccess: () => { navigate(`/adv/campaigns/${placement.id}/published`) } },
            )
          }}
        >
          {isPending ? '⏳ Оплата...' : '💳 Оплатить и запустить кампанию'}
        </Button>

        <Button
          variant="danger"
          fullWidth
          disabled={isPending}
          onClick={() => {
            haptic.warning()
            updatePlacement(
              { id: placement.id, data: { action: 'cancel' } },
              { onSuccess: () => { navigate('/adv/campaigns') } },
            )
          }}
        >
          ❌ Отменить заявку
        </Button>
      </div>

      <Notification type="warning">
        <span style={{ fontSize: 'var(--rh-text-xs)' }}>
          ⚠️ Отмена после оплаты: возврат 50%
        </span>
      </Notification>
    </ScreenShell>
  )
}
