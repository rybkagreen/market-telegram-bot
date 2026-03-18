import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { ArbitrationPanel, Button, Card, Notification, Skeleton } from '@/components/ui'
import { PUBLICATION_FORMATS, MAX_COUNTER_OFFERS, MIN_REJECTION_COMMENT } from '@/lib/constants'
import { formatCurrency, formatDateTime } from '@/lib/formatters'
import { useHaptic } from '@/hooks/useHaptic'
import { usePlacement, useUpdatePlacement } from '@/hooks/queries'
import styles from './OwnRequestDetail.module.css'

export default function OwnRequestDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const haptic = useHaptic()

  const numId = id ? parseInt(id) : null
  const { data: request, isLoading } = usePlacement(numId)
  const { mutate: updatePlacement, isPending } = useUpdatePlacement()

  const [counterPrice, setCounterPrice] = useState('')
  const [counterTime, setCounterTime] = useState('14:00')
  const [rejectionText, setRejectionText] = useState('')

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={200} />
        <Skeleton height={100} />
        <Skeleton height={120} />
      </ScreenShell>
    )
  }

  if (!request) {
    return (
      <ScreenShell>
        <Notification type="danger">Заявка не найдена</Notification>
      </ScreenShell>
    )
  }

  const fmt = PUBLICATION_FORMATS[request.publication_format]
  const proposedNum = parseFloat(request.proposed_price)

  const handleAccept = () => {
    haptic.success()
    updatePlacement(
      { id: request.id, data: { action: 'accept' } },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  const handleCounter = () => {
    haptic.tap()
    const today = new Date().toISOString().substring(0, 10)
    updatePlacement({
      id: request.id,
      data: {
        action: 'counter',
        price: parseFloat(counterPrice) || proposedNum,
        schedule: `${today}T${counterTime}:00`,
      },
    })
  }

  const handleReject = () => {
    haptic.warning()
    updatePlacement(
      { id: request.id, data: { action: 'reject', comment: rejectionText } },
      { onSuccess: () => navigate('/own/requests') },
    )
  }

  return (
    <ScreenShell>
      <ArbitrationPanel title={`Заявка #${request.id} · @${request.channel?.username ?? request.channel_id}`}>
        <div className={styles.infoRows}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Формат</span>
            <span className={styles.infoValue}>{fmt.icon} {fmt.name}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Предложение</span>
            <span className={styles.infoAccent}>{formatCurrency(request.proposed_price)}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Время</span>
            <span className={styles.infoValue}>
              {request.proposed_schedule ? formatDateTime(request.proposed_schedule) : '—'} ✅
            </span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Частота</span>
            <span className={styles.infoValue}>1 пост</span>
          </div>
        </div>
      </ArbitrationPanel>

      <p className={styles.sectionTitle}>Текст объявления</p>
      <Card>
        <p className={styles.adText}>{request.ad_text}</p>
      </Card>

      {request.status === 'pending_owner' && (
        <>
          <Button variant="success" fullWidth onClick={handleAccept} disabled={isPending}>
            {isPending ? '⏳ Обработка...' : '✅ Принять условия'}
          </Button>

          <p className={styles.sectionTitle}>Контр-предложение</p>
          {request.counter_offer_count < MAX_COUNTER_OFFERS ? (
            <>
              <div className={styles.counterGrid}>
                <div className={styles.counterField}>
                  <label className={styles.label}>Ваша цена</label>
                  <input
                    className={styles.input}
                    type="number"
                    value={counterPrice || String(Math.round(proposedNum))}
                    onChange={(e) => setCounterPrice(e.target.value)}
                  />
                </div>
                <div className={styles.counterField}>
                  <label className={styles.label}>Время</label>
                  <input
                    className={styles.input}
                    type="time"
                    value={counterTime}
                    onChange={(e) => setCounterTime(e.target.value)}
                  />
                </div>
              </div>
              <Button variant="secondary" fullWidth onClick={handleCounter} disabled={isPending}>
                ✏️ Отправить контр-предложение
              </Button>
            </>
          ) : (
            <Notification type="warning">
              <span style={{ fontSize: 'var(--rh-text-sm)' }}>
                Максимум {MAX_COUNTER_OFFERS} раунда контр-предложений исчерпано
              </span>
            </Notification>
          )}

          <p className={styles.sectionTitle}>Отклонить</p>
          <textarea
            className={styles.textarea}
            placeholder={`Причина отклонения (обязательно, мин. ${MIN_REJECTION_COMMENT} символов)`}
            value={rejectionText}
            onChange={(e) => setRejectionText(e.target.value)}
            rows={3}
          />
          <p className={styles.hintWarning}>⚠️ Необоснованный отказ: −10 к репутации</p>
          <Button
            variant="danger"
            fullWidth
            disabled={rejectionText.length < MIN_REJECTION_COMMENT || isPending}
            onClick={handleReject}
          >
            ❌ Отклонить заявку
          </Button>
        </>
      )}

      {request.status === 'published' && request.published_at && request.final_price && (
        <Card>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Опубликовано</span>
            <span className={styles.infoValue}>{formatDateTime(request.published_at)}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Заработано</span>
            <span className={styles.infoEarned}>
              {formatCurrency(parseFloat(request.final_price) * 0.85)}
            </span>
          </div>
        </Card>
      )}

      {request.status === 'cancelled' && request.rejection_reason && (
        <Card>
          <div className={styles.rejectionReason}>
            <span className={styles.infoLabel}>Причина отклонения</span>
            <p className={styles.reasonText}>{request.rejection_reason}</p>
          </div>
        </Card>
      )}
    </ScreenShell>
  )
}
