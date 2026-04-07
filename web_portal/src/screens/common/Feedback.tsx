import { useState } from 'react'
import { Card, Button, Notification } from '@shared/ui'
import { api } from '@shared/api/client'

export default function Feedback() {
  const [text, setText] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!text.trim()) {
      setError('Введите текст обращения')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await api.post('feedback', { json: { text } })
      setSubmitted(true)
    } catch {
      setError('Не удалось отправить обращение. Попробуйте позже.')
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <Card title="Обратная связь">
        <Notification type="success">
          Ваше обращение отправлено. Мы ответим в ближайшее время.
        </Notification>
      </Card>
    )
  }

  return (
    <Card title="Обратная связь">
      <div className="space-y-4 max-w-xl">
        {error && (
          <Notification type="danger">
            <span>{error}</span>
          </Notification>
        )}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Опишите вашу проблему или предложение
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 rounded-md border border-border-active bg-harbor-elevated text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-2 focus:ring-accent resize-none"
            placeholder="Подробно опишите ваш вопрос..."
          />
        </div>
        <Button onClick={handleSubmit} loading={loading} disabled={!text.trim()}>
          Отправить
        </Button>
      </div>
    </Card>
  )
}
