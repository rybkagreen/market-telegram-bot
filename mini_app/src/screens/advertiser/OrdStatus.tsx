import { useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Skeleton, StatusPill, Notification, Text } from '@/components/ui'
import { useOrdStatus } from '@/hooks/useOrdQueries'
import type { OrdStatus as OrdStatusType } from '@/lib/types'
import styles from './OrdStatus.module.css'

const STATUS_LABELS: Record<OrdStatusType, string> = {
  pending: 'Ожидание регистрации',
  registered: 'Зарегистрирован',
  token_received: 'Токен получен',
  reported: 'Отчёт отправлен',
  failed: 'Ошибка',
}

const STATUS_PILL_MAP: Record<OrdStatusType, 'warning' | 'info' | 'success' | 'danger'> = {
  pending: 'warning',
  registered: 'info',
  token_received: 'success',
  reported: 'success',
  failed: 'danger',
}

export default function OrdStatus() {
  const { id } = useParams<{ id: string }>()
  const numId = id ? parseInt(id, 10) : undefined
  const { data: ord, isLoading } = useOrdStatus(numId)

  return (
    <ScreenShell>
      <Text variant="lg" weight="bold" font="display" className={styles.title}>
        Маркировка рекламы (ORD)
      </Text>

      {isLoading ? (
        <>
          <Skeleton height={60} />
          <Skeleton height={60} />
        </>
      ) : !ord ? (
        <Notification type="info">Данные ORD не найдены</Notification>
      ) : (
        <>
          <div className={styles.statusWrapper}>
            <StatusPill status={STATUS_PILL_MAP[ord.status]}>
              {STATUS_LABELS[ord.status]}
            </StatusPill>
          </div>

          {ord.erid && (
            <div className={styles.eridBox}>
              Токен erid: <strong>{ord.erid}</strong>
            </div>
          )}

          {ord.status === 'failed' && ord.error_message && (
            <Notification type="danger">{ord.error_message}</Notification>
          )}

          {ord.status === 'pending' && (
            <Text variant="xs" color="muted" align="center" className={styles.pendingHint}>
              Обновляется автоматически...
            </Text>
          )}
        </>
      )}
    </ScreenShell>
  )
}
