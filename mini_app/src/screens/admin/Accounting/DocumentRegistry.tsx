/**
 * DocumentRegistry — Реестр бухгалтерских документов
 *
 * Загружает договоры с GET /admin/contracts (limit=20).
 * Примечание: эндпоинты /admin/acts и /admin/invoices пока не реализованы
 * на бэкенде — реестр работает с доступными данными.
 */

import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import { Text } from '@/components/ui'
import * as Sentry from '@sentry/react'
import styles from './accounting.module.css'

interface DocItem {
  id: number
  user_id: number
  contract_type: string
  contract_status: string
  signed_at: string | null
  created_at: string
  template_version: string | null
}

const TYPE_LABELS: Record<string, string> = {
  platform_rules: '📋 Правила',
  privacy_policy: '🔒 Конфиденц.',
  owner_service: '🤝 Договор владельца',
  advertiser_campaign: '📢 Рекламная кампания',
  advertiser_framework: '📑 Рамочный договор',
}

const STATUS_LABELS: Record<string, string> = {
  signed: 'Подписан',
  pending: 'Ожидает',
  draft: 'Черновик',
  expired: 'Истёк',
  cancelled: 'Отменён',
}

export default function DocumentRegistry() {
  const [docs, setDocs] = useState<DocItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchDocs = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await api
          .get('admin/contracts', { searchParams: { limit: 20 } })
          .json<{ items: DocItem[]; total: number }>()
        setDocs(data.items)
      } catch (err) {
        Sentry.captureException(err)
        setError('Не удалось загрузить реестр документов')
      } finally {
        setLoading(false)
      }
    }

    fetchDocs()
  }, [])

  return (
    <div className={styles.card}>
      <Text variant="lg" weight="semibold" font="display" className={styles.cardTitle}>
        📑 Реестр документов
      </Text>

      {loading ? (
        <div className={styles.skeletonWrap}>
          <div className={styles.skeletonLine} style={{ width: '25%' }} />
          {[1, 2, 3].map((i) => (
            <div key={i} className={styles.skeletonLine} />
          ))}
        </div>
      ) : error ? (
        <Text variant="sm" color="danger">{error}</Text>
      ) : docs.length === 0 ? (
        <Text variant="sm" color="muted" align="center">Документов пока нет</Text>
      ) : (
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Тип</th>
                <th>№</th>
                <th>Дата</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc, idx) => (
                <tr key={doc.id} className={idx % 2 === 0 ? '' : styles.evenRow}>
                  <td>{TYPE_LABELS[doc.contract_type] || doc.contract_type}</td>
                  <td className={styles.mono}>#{doc.id}</td>
                  <td>
                    {doc.signed_at
                      ? new Date(doc.signed_at).toLocaleDateString('ru-RU')
                      : new Date(doc.created_at).toLocaleDateString('ru-RU')}
                  </td>
                  <td>
                    <span className={`${styles.statusPill} ${styles[doc.contract_status] || ''}`}>
                      {STATUS_LABELS[doc.contract_status] || doc.contract_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
