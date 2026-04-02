import { useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Skeleton, StatusPill, Notification } from '@/components/ui'
import { useOrdStatus } from '@/hooks/useOrdQueries'
import type { OrdStatus as OrdStatusType } from '@/lib/types'

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
      <p style={{ fontWeight: 700, fontSize: 'var(--rh-text-lg, 18px)', marginBottom: 16 }}>
        Маркировка рекламы (ORD)
      </p>

      {isLoading ? (
        <>
          <Skeleton height={60} />
          <Skeleton height={60} />
        </>
      ) : !ord ? (
        <Notification type="info">Данные ORD не найдены</Notification>
      ) : (
        <>
          <div style={{ marginBottom: 12 }}>
            <StatusPill status={STATUS_PILL_MAP[ord.status]}>
              {STATUS_LABELS[ord.status]}
            </StatusPill>
          </div>

          {ord.erid && (
            <div
              style={{
                padding: '10px 16px',
                borderRadius: 'var(--rh-radius-sm, 8px)',
                background: 'var(--rh-surface, rgba(255,255,255,0.04))',
                fontFamily: 'monospace',
                fontSize: 'var(--rh-text-sm, 14px)',
                marginBottom: 12,
              }}
            >
              Токен erid: <strong>{ord.erid}</strong>
            </div>
          )}

          {ord.status === 'failed' && ord.error_message && (
            <Notification type="danger">{ord.error_message}</Notification>
          )}

          {ord.status === 'pending' && (
            <p
              style={{
                fontSize: 'var(--rh-text-xs, 12px)',
                color: 'var(--rh-text-muted)',
                textAlign: 'center',
                marginTop: 16,
              }}
            >
              Обновляется автоматически...
            </p>
          )}
        </>
      )}
    </ScreenShell>
  )
}
