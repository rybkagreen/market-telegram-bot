import { useState } from 'react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Notification } from '@/components/ui/Notification'
import { useHaptic } from '@/hooks/useHaptic'
import { useCreateFeedback, useMyFeedback } from '@/hooks/queries/useFeedbackQueries'
import styles from './Feedback.module.css'

export default function Feedback() {
  const haptic = useHaptic()
  const [text, setText] = useState('')
  const createMutation = useCreateFeedback()
  const { data: feedbackList, isLoading } = useMyFeedback()

  const handleSubmit = () => {
    haptic.tap()
    if (!text.trim()) return
    createMutation.mutate(text)
    setText('')
  }

  return (
    <ScreenShell>
      <Notification type="info">
        📝 Напишите ваше сообщение
      </Notification>

      <Card className={styles.card}>
        <textarea
          className={styles.textarea}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Опишите вашу проблему или предложение..."
          rows={6}
        />
      </Card>

      <Button
        variant="primary"
        fullWidth
        onClick={handleSubmit}
        disabled={!text.trim() || createMutation.isPending}
      >
        {createMutation.isPending ? '⏳ Отправка...' : '✉️ Отправить в поддержку'}
      </Button>

      {/* История feedback */}
      {isLoading ? (
        <Notification type="info">Загрузка истории...</Notification>
      ) : feedbackList && feedbackList.items.length > 0 ? (
        <Card title="📋 История обращений" className={styles.card}>
          {feedbackList.items.map((feedback) => (
            <div key={feedback.id} className={styles.feedbackItem}>
              <div className={styles.feedbackHeader}>
                <span className={styles.statusBadge}>{feedback.status}</span>
                <span className={styles.feedbackDate}>
                  {new Date(feedback.created_at).toLocaleDateString()}
                </span>
              </div>
              <p className={styles.feedbackText}>{feedback.text}</p>
              {feedback.admin_response && (
                <div className={styles.adminResponse}>
                  <strong>Ответ поддержки:</strong>
                  <p>{feedback.admin_response}</p>
                </div>
              )}
            </div>
          ))}
        </Card>
      ) : null}
    </ScreenShell>
  )
}
