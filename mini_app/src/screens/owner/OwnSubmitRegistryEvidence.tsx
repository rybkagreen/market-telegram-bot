import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button, Card, Notification, Text } from '@/components/ui'
import { useHaptic } from '@/hooks/useHaptic'
import { useSubmitRegistryEvidence } from '@/hooks/queries/useChannelQueries'
import styles from './OwnSubmitRegistryEvidence.module.css'

export default function OwnSubmitRegistryEvidence() {
  const navigate = useNavigate()
  const haptic = useHaptic()
  const { id } = useParams()
  const channelId = id ? parseInt(id) : null

  const [applicationNumber, setApplicationNumber] = useState('')
  const [registryUrl, setRegistryUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const submitMutation = useSubmitRegistryEvidence()

  const validate = (): boolean => {
    const nextErrors: Record<string, string> = {}
    const trimmedNum = applicationNumber.trim()
    if (!trimmedNum) {
      nextErrors.applicationNumber = 'Укажите номер заявления'
    } else if (trimmedNum.length > 64) {
      nextErrors.applicationNumber = 'Не более 64 символов'
    }
    const trimmedUrl = registryUrl.trim()
    if (trimmedUrl) {
      try {
        new URL(trimmedUrl)
      } catch {
        nextErrors.registryUrl = 'Некорректный URL'
      }
    }
    if (notes.length > 1000) {
      nextErrors.notes = 'Не более 1000 символов'
    }
    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const handleSubmit = () => {
    if (!channelId) return
    if (!validate()) return
    haptic.tap()
    submitMutation.mutate(
      {
        channelId,
        data: {
          application_number: applicationNumber.trim(),
          registry_url: registryUrl.trim() || null,
          notes: notes.trim() || null,
        },
      },
      {
        onSuccess: () => {
          haptic.success()
          navigate(`/own/channels/${channelId}`)
        },
      },
    )
  }

  if (!channelId) {
    return (
      <ScreenShell>
        <Notification type="danger">
          <Text variant="sm">❌ Канал не найден</Text>
        </Notification>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell>
      <Card>
        <Text variant="lg">📋 Подача заявки на верификацию</Text>
        <Text variant="sm">
          Этот канал требует регистрации в реестре блогеров (ФЗ-303). Если @Trustchannelbot
          не добавлен как администратор, отправьте номер заявления с Госуслуг — администратор
          подтвердит регистрацию вручную.
        </Text>
      </Card>

      <div className={styles.field}>
        <label className={styles.label}>
          Номер заявления<span className={styles.required}>*</span>
        </label>
        <input
          className={`${styles.input} ${errors.applicationNumber ? styles.invalid : ''}`}
          type="text"
          placeholder="A-2026-04-12345"
          value={applicationNumber}
          maxLength={64}
          onChange={(e) => setApplicationNumber(e.target.value)}
        />
        <p className={styles.hint}>Номер заявления на регистрацию в реестре блогеров (Госуслуги)</p>
        {errors.applicationNumber && (
          <p className={styles.error}>{errors.applicationNumber}</p>
        )}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Ссылка на запись в реестре</label>
        <input
          className={`${styles.input} ${errors.registryUrl ? styles.invalid : ''}`}
          type="url"
          placeholder="https://rkn.gov.ru/..."
          value={registryUrl}
          onChange={(e) => setRegistryUrl(e.target.value)}
        />
        <p className={styles.hint}>Опционально, если есть публичная ссылка</p>
        {errors.registryUrl && <p className={styles.error}>{errors.registryUrl}</p>}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Комментарий</label>
        <textarea
          className={`${styles.textarea} ${errors.notes ? styles.invalid : ''}`}
          placeholder="Дополнительные сведения для администратора"
          value={notes}
          maxLength={1000}
          onChange={(e) => setNotes(e.target.value)}
        />
        <p className={styles.hint}>Опционально, до 1000 символов</p>
        {errors.notes && <p className={styles.error}>{errors.notes}</p>}
      </div>

      <Button
        fullWidth
        variant="primary"
        onClick={handleSubmit}
        disabled={submitMutation.isPending}
      >
        {submitMutation.isPending ? '⏳ Отправка…' : '📤 Отправить заявку'}
      </Button>

      <Button fullWidth variant="ghost" onClick={() => navigate(`/own/channels/${channelId}`)}>
        Отмена
      </Button>
    </ScreenShell>
  )
}
