import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button, Card, Notification } from '@/components/ui'
import { useHaptic } from '@/hooks/useHaptic'
import { useCheckChannel, useAddChannel } from '@/hooks/queries/useChannelQueries'
import styles from './OwnAddChannel.module.css'

export default function OwnAddChannel() {
  const navigate = useNavigate()
  const haptic = useHaptic()
  const [username, setUsername] = useState('')

  const checkMutation = useCheckChannel()
  const addMutation = useAddChannel()

  const checkResult = checkMutation.data ?? null

  const handleCheck = () => {
    haptic.tap()
    const clean = username.startsWith('@') ? username.slice(1) : username
    checkMutation.mutate(clean)
  }

  const handleAdd = () => {
    haptic.success()
    const clean = username.startsWith('@') ? username.slice(1) : username
    addMutation.mutate(
      { username: clean },
      {
        onSuccess: () => {
          navigate('/own/channels')
        },
      },
    )
  }

  return (
    <ScreenShell>
      <Notification type="warning">
        <span style={{ fontSize: 'var(--rh-text-sm)' }}>
          ⚠️ Перед добавлением выдайте боту права: удалять сообщения и закреплять сообщения
        </span>
      </Notification>

      <div className={styles.field}>
        <label className={styles.label}>Username канала</label>
        <input
          className={styles.input}
          type="text"
          placeholder="@my_channel"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>

      <Button fullWidth onClick={handleCheck} disabled={checkMutation.isPending || !username}>
        {checkMutation.isPending ? '⏳ Проверка...' : '🔍 Проверить канал'}
      </Button>

      {checkResult !== null && (
        <>
          <Card title="Результат проверки" className={styles.resultCard}>
            <div className={styles.resultRow}>
              <span className={styles.resultLabel}>Статус</span>
              <span className={checkResult.valid ? styles.resultGreen : styles.resultRed}>
                {checkResult.valid ? '✅ Канал доступен' : '❌ Канал недоступен'}
              </span>
            </div>
          </Card>

          {checkResult.valid && (
            <Button
              variant="success"
              fullWidth
              onClick={handleAdd}
              disabled={addMutation.isPending}
            >
              {addMutation.isPending ? '⏳ Добавление...' : '➕ Добавить канал'}
            </Button>
          )}

          {!checkResult.valid && (
            <Notification type="danger">
              <span style={{ fontSize: 'var(--rh-text-sm)' }}>
                ❌ Канал недоступен. Проверьте права бота и попробуйте снова.
              </span>
            </Notification>
          )}
        </>
      )}
    </ScreenShell>
  )
}
