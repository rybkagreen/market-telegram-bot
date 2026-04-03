import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Notification, FeeBreakdown, Button, Skeleton, Card } from '@/components/ui'
import { PUBLICATION_FORMATS } from '@/lib/constants'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import { useContracts } from '@/hooks/useContractQueries'
import { useUiStore } from '@/stores/uiStore'
import styles from './CampaignPayment.module.css'

export default function CampaignPayment() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id, 10) : null
  const { data: placement, isLoading } = usePlacement(numId)
  const { mutate: updatePlacement, isPending } = useUpdatePlacement()
  const { data: contractsList, isLoading: contractsLoading } = useContracts('advertiser_framework')
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)
  const hasSubmitted = useRef(false)

  const isExpired = placement?.expires_at ? new Date(placement.expires_at) < new Date() : false

  // If already paid (escrow/published) — redirect to waiting/published
  useEffect(() => {
    if (!placement) return
    if (placement.status === 'escrow' || placement.status === 'pending_owner' || placement.status === 'counter_offer') {
      if (placement.status === 'escrow') {
        navigate(`/adv/campaigns/${placement.id}/waiting`, { replace: true })
      }
    }
    if (placement.status === 'published') {
      navigate(`/adv/campaigns/${placement.id}/published`, { replace: true })
    }
    if (placement.status === 'cancelled' || placement.status === 'failed' || placement.status === 'refunded') {
      navigate('/adv/campaigns', { replace: true })
    }
    // Redirect expired placements back to campaigns list
    if (isExpired && (placement.status === 'pending_payment' || placement.status === 'counter_offer')) {
      navigate('/adv/campaigns', { replace: true })
    }
  }, [placement?.status, isExpired]) // eslint-disable-line react-hooks/exhaustive-deps

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
  const originalPrice = placement.proposed_price

  const frameworkRef = frameworkContract
    ? `рамочному договору №${frameworkContract.id} от ${new Date(frameworkContract.signed_at!).toLocaleDateString('ru-RU')}`
    : 'рамочному договору'

  // Counter offer mode
  const isCounterOffer = placement.status === 'counter_offer'

  // Test mode warning
  const isTest = placement.is_test

  return (
    <ScreenShell>
      {isCounterOffer ? (
        <Notification type="warning">
          ✏️ Владелец предложил другие условия
        </Notification>
      ) : (
        <Notification type="success">✅ Владелец принял условия!</Notification>
      )}

      {isTest && (
        <Notification type="info">
          🧪 <b>Тестовая кампания</b><br/>
          Оплата не требуется. Кампания будет создана в тестовом режиме без реального списания средств.
        </Notification>
      )}

      {isCounterOffer && (
        <Card title="📋 Контрпредложение владельца" className={styles.card}>
          <div className={styles.counterOfferRows}>
            <div className={styles.row}>
              <span className={styles.label}>💰 Оригинальная цена:</span>
              <span className={styles.originalPrice}>{formatCurrency(originalPrice)}</span>
            </div>
            <div className={styles.row}>
              <span className={styles.label}>💵 Новая цена:</span>
              <span className={styles.newPrice}>{formatCurrency(price)}</span>
            </div>
            {placement.counter_comment && (
              <div className={styles.commentRow}>
                <span className={styles.label}>💬 Комментарий:</span>
                <p className={styles.comment}>{placement.counter_comment}</p>
              </div>
            )}
            <div className={styles.row}>
              <span className={styles.label}>📅 Раунд:</span>
              <span className={styles.value}>{placement.counter_offer_count}/3</span>
            </div>
          </div>
        </Card>
      )}

      <p className={styles.sectionTitle}>К оплате</p>

      <FeeBreakdown
        rows={[
          {
            label: `@${placement.channel?.username ?? `#${placement.channel_id}`} · ${formatInfo.name}`,
            value: formatCurrency(price),
          },
          {
            label: 'Комиссия платформы (15%)',
            value: isCounterOffer ? 'включена в новую цену' : 'включена',
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

        {isCounterOffer && (
          <Button
            variant="secondary"
            fullWidth
            disabled={isPending}
            onClick={() => {
              if (hasSubmitted.current) return
              hasSubmitted.current = true
              haptic.success()
              updatePlacement(
                { id: placement.id, data: { action: 'accept-counter' } },
                {
                  onSuccess: () => { navigate(`/adv/campaigns/${placement.id}/waiting`) },
                  onError: (err) => {
                    hasSubmitted.current = false
                    if ((err as { response?: { status?: number } })?.response?.status === 409) {
                      queryClient.invalidateQueries({ queryKey: ['placements', placement.id] })
                      addToast('warning', 'Статус заявки изменился, страница обновлена')
                    }
                  },
                },
              )
            }}
          >
            {isPending ? '⏳ Принятие...' : '✏️ Принять контрпредложение'}
          </Button>
        )}

        <Button
          variant="primary"
          fullWidth
          disabled={isPending}
          onClick={() => {
            if (hasSubmitted.current) return
            hasSubmitted.current = true
            haptic.success()
            updatePlacement(
              { id: placement.id, data: { action: 'pay' } },
              {
                onSuccess: () => { navigate(`/adv/campaigns/${placement.id}/waiting`) },
                onError: (err) => {
                  hasSubmitted.current = false
                  if ((err as { response?: { status?: number } })?.response?.status === 409) {
                    queryClient.invalidateQueries({ queryKey: ['placements', placement.id] })
                    addToast('warning', 'Статус заявки изменился, страница обновлена')
                  }
                },
              },
            )
          }}
        >
          {isPending ? '⏳ Оплата...' : isCounterOffer ? '💳 Оплатить (принять условия)' : '💳 Оплатить и запустить кампанию'}
        </Button>

        <Button
          variant="danger"
          fullWidth
          disabled={isPending}
          onClick={() => {
            if (hasSubmitted.current) return
            hasSubmitted.current = true
            haptic.warning()
            updatePlacement(
              { id: placement.id, data: { action: 'cancel' } },
              {
                onSuccess: () => { navigate('/adv/campaigns') },
                onError: (err) => {
                  hasSubmitted.current = false
                  if ((err as { response?: { status?: number } })?.response?.status === 409) {
                    queryClient.invalidateQueries({ queryKey: ['placements', placement.id] })
                    addToast('warning', 'Статус заявки изменился, страница обновлена')
                  }
                },
              },
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
