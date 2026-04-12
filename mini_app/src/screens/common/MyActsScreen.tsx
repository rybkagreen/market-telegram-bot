/**
 * MyActsScreen — Список актов пользователя с возможностью подписания
 *
 * Загружает акты через GET /api/acts/mine.
 * Отображает: тип (ИСХ/ВХ), номер, дату, статус, кнопку «Подписать».
 */

import { useEffect, useState } from 'react'
import { ScreenLayout } from '@/components/layout/ScreenLayout'
import { Skeleton, EmptyState, Button, Icon, Text, Flex } from '@/components/ui'
import { formatDateMSK } from '@/lib/constants'
import { api } from '@/api/client'
import * as Sentry from '@sentry/react'
import styles from './MyActsScreen.module.css'

interface ActItem {
  id: number
  act_number: string
  act_type: string
  act_date: string
  sign_status: string
  signed_at: string | null
  sign_method: string | null
  pdf_url: string | null
  placement_request_id: number
  created_at: string
}

const TYPE_LABELS: Record<string, string> = {
  income: '📤 Акт-ИСХ',
  expense: '📥 Акт-ВХ',
}

const STATUS_LABELS: Record<string, string> = {
  draft: 'Черновик',
  pending: 'Ожидает',
  signed: 'Подписан',
  auto_signed: 'Авто-подписан',
}

export default function MyActsScreen() {
  const [acts, setActs] = useState<ActItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [signingId, setSigningId] = useState<number | null>(null)

  const fetchActs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get('acts/mine', { searchParams: { limit: 50 } }).json<{ items: ActItem[] }>()
      setActs(data.items)
    } catch (err) {
      Sentry.captureException(err)
      setError('Не удалось загрузить акты')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchActs()
  }, [])

  const handleSign = async (actId: number) => {
    setSigningId(actId)
    try {
      await api.post(`acts/${actId}/sign`).json<{ id: number; sign_status: string }>()
      setActs((prev) =>
        prev.map((a) => (a.id === actId ? { ...a, sign_status: 'signed' } : a))
      )
    } catch (err) {
      Sentry.captureException(err)
      alert('Ошибка при подписании акта')
    } finally {
      setSigningId(null)
    }
  }

  const handleDownloadPdf = async (actId: number) => {
    try {
      const response = await api.get(`acts/${actId}/pdf`, { timeout: 30_000 })
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `act_${actId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      Sentry.captureException(err)
      alert('Ошибка при скачивании PDF')
    }
  }

  if (loading) {
    return (
      <ScreenLayout title="Мои акты">
        <Skeleton height={80} />
        <Skeleton height={80} />
      </ScreenLayout>
    )
  }

  if (error) {
    return (
      <ScreenLayout title="Мои акты">
        <Text variant="sm" color="danger">{error}</Text>
        <Button variant="primary" size="sm" onClick={fetchActs}>
          <Icon name="RefreshCw" size={16} /> Повторить
        </Button>
      </ScreenLayout>
    )
  }

  if (acts.length === 0) {
    return (
      <ScreenLayout title="Мои акты">
        <EmptyState icon="📄" title="Актов пока нет" description="Акты появятся после завершения размещений" />
      </ScreenLayout>
    )
  }

  return (
    <ScreenLayout title="Мои акты">
      {acts.map((act) => {
        const canSign = act.sign_status === 'draft' || act.sign_status === 'pending'

        return (
          <div key={act.id} className={styles.actCard}>
            <Flex justify="between" align="start">
              <div>
                <Text variant="sm" weight="semibold">
                  {TYPE_LABELS[act.act_type] || act.act_type} №{act.act_number}
                </Text>
                <Text variant="xs" color="muted">
                  от {formatDateMSK(act.act_date)}
                </Text>
              </div>
              <span className={`${styles.statusPill} ${styles[act.sign_status] || ''}`}>
                {STATUS_LABELS[act.sign_status] || act.sign_status}
              </span>
            </Flex>

            {(canSign || act.pdf_url) && (
              <Flex gap={2} className={styles.actionRow}>
                {canSign && (
                  <Button
                    variant="success"
                    size="sm"
                    fullWidth
                    loading={signingId === act.id}
                    onClick={() => handleSign(act.id)}
                  >
                    {signingId === act.id ? 'Подписание...' : 'Подписать'}
                  </Button>
                )}
                {act.pdf_url && (
                  <Button variant="secondary" size="sm" fullWidth onClick={() => handleDownloadPdf(act.id)}>
                    <Icon name="Download" size={16} /> Скачать PDF
                  </Button>
                )}
              </Flex>
            )}
          </div>
        )
      })}
    </ScreenLayout>
  )
}
