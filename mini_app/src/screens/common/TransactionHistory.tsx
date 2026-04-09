import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Skeleton, Notification } from '@/components/ui'
import type { TransactionType } from '@/api/billing'
import { useBillingHistory } from '@/hooks/queries'
import styles from './TransactionHistory.module.css'

// ─── Метаданные типов транзакций ───────────────────────────────────────────

interface TxMeta {
  label: string
  icon: string
  /** true = деньги/кредиты поступили, false = ушли */
  incoming: boolean
}

const TX_META: Record<string, TxMeta> = {
  topup:         { label: 'Пополнение баланса',      icon: '💳', incoming: true  },
  escrow_freeze: { label: 'Оплата эскроу',           icon: '🔒', incoming: false },
  escrow_release:{ label: 'Получение выплаты',       icon: '✅', incoming: true  },
  spend:         { label: 'Оплата тарифа',           icon: '⭐', incoming: false },
  payout:        { label: 'Вывод средств',           icon: '💸', incoming: false },
  payout_fee:    { label: 'Комиссия за вывод',       icon: '📋', incoming: false },
  refund_full:   { label: 'Возврат средств',         icon: '↩️', incoming: true  },
  bonus:         { label: 'Бонус',                   icon: '🎁', incoming: true  },
}

const STATUS_LABEL: Record<string, string> = {
  completed: 'Выполнено',
  succeeded: 'Выполнено',
  pending:   'В обработке',
  canceled:  'Отменено',
  failed:    'Ошибка',
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatAmount(amount: number, incoming: boolean): string {
  const sign = incoming ? '+' : '−'
  return `${sign}${amount.toLocaleString('ru-RU')} ₽`
}

// ─── Компонент ─────────────────────────────────────────────────────────────

export default function TransactionHistory() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const { data, isLoading, isError } = useBillingHistory(page)

  return (
    <ScreenShell>
      <Card title="История транзакций">
        {isLoading ? (
          <>
            <Skeleton height={64} />
            <Skeleton height={64} />
            <Skeleton height={64} />
          </>
        ) : isError ? (
          <Notification type="danger">Не удалось загрузить историю</Notification>
        ) : !data || data.items.length === 0 ? (
          <Notification type="info">Транзакций пока нет</Notification>
        ) : (
          <div className={styles.list}>
            {data.items.map((item) => {
              const meta = TX_META[item.type as TransactionType] ?? {
                label: item.type,
                icon: '📄',
                incoming: true,
              }
              const statusText = STATUS_LABEL[item.status] ?? item.status

              return (
                <div key={item.id} className={styles.item}>
                  <div className={styles.icon}>{meta.icon}</div>

                  <div className={styles.middle}>
                    <span className={styles.label}>{meta.label}</span>
                    {item.description && (
                      <span className={styles.desc}>{item.description}</span>
                    )}
                    <div className={styles.meta}>
                      <span className={styles.date}>{formatDate(item.created_at)}</span>
                      {item.placement_request_id && (
                        <span className={styles.ref}>
                          · заявка #{item.placement_request_id}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className={styles.right}>
                    <span
                      className={`${styles.amount} ${meta.incoming ? styles.amountIn : styles.amountOut}`}
                    >
                      {formatAmount(Number(item.amount), meta.incoming)}
                    </span>
                    <span
                      className={`${styles.status} ${
                        item.status === 'pending' ? styles.statusPending : styles.statusDone
                      }`}
                    >
                      {statusText}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {data && data.pages > 1 && (
        <div className={styles.pagination}>
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ← Назад
          </Button>
          <span className={styles.pageInfo}>{page} / {data.pages}</span>
          <Button variant="secondary" size="sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
            Вперёд →
          </Button>
        </div>
      )}

      <Button variant="secondary" fullWidth onClick={() => navigate('/cabinet')}>
        ← Назад в кабинет
      </Button>
    </ScreenShell>
  )
}
