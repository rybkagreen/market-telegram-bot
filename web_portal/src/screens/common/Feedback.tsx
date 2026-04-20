import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Icon, ScreenHeader, Notification } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useCreateFeedback } from '@/hooks/useFeedbackQueries'

type Tone = 'danger' | 'warning' | 'info' | 'neutral'

interface TopicConf {
  id: string
  label: string
  icon: IconName
  tone: Tone
}

const TOPICS: TopicConf[] = [
  { id: 'bug', label: 'Ошибка', icon: 'warning', tone: 'danger' },
  { id: 'payment', label: 'Оплата / возврат', icon: 'wallet', tone: 'warning' },
  { id: 'idea', label: 'Предложение', icon: 'zap', tone: 'info' },
  { id: 'content', label: 'Модерация', icon: 'lock', tone: 'info' },
  { id: 'other', label: 'Другое', icon: 'feedback', tone: 'neutral' },
]

interface PriorityConf {
  id: string
  label: string
  sub: string
}

const PRIORITIES: PriorityConf[] = [
  { id: 'low', label: 'Не срочно', sub: 'Ответ 1–2 дня' },
  { id: 'normal', label: 'Обычный', sub: '≈ 14 минут' },
  { id: 'high', label: 'Срочно', sub: 'Блокирует работу' },
]

const SUGGESTIONS = [
  'Не проходит оплата картой',
  'Как отменить кампанию',
  'Не получил выплату',
  'Проблема с подписанием акта',
  'Ошибка в аналитике',
]

interface SideChannel {
  icon: IconName
  title: string
  sub: string
}

const SIDE_CHANNELS: SideChannel[] = [
  { icon: 'telegram', title: '@RekHarborSupport', sub: 'Telegram' },
  { icon: 'email', title: 'help@rekharbor.ru', sub: 'Email' },
]

const MAX_LEN = 1200
const MIN_LEN = 20

const toneMap: Record<Tone, { border: string; bg: string; text: string; iconBg: string; iconText: string }> = {
  danger: {
    border: 'border-danger',
    bg: 'bg-danger/10',
    text: 'text-danger',
    iconBg: 'bg-danger-muted',
    iconText: 'text-danger',
  },
  warning: {
    border: 'border-warning',
    bg: 'bg-warning/10',
    text: 'text-warning',
    iconBg: 'bg-warning-muted',
    iconText: 'text-warning',
  },
  info: {
    border: 'border-accent',
    bg: 'bg-accent-muted',
    text: 'text-accent',
    iconBg: 'bg-accent-muted',
    iconText: 'text-accent',
  },
  neutral: {
    border: 'border-border',
    bg: 'bg-harbor-elevated',
    text: 'text-text-secondary',
    iconBg: 'bg-harbor-elevated',
    iconText: 'text-text-secondary',
  },
}

export default function Feedback() {
  const navigate = useNavigate()
  const createFeedback = useCreateFeedback()
  const [topic, setTopic] = useState('bug')
  const [priority, setPriority] = useState('normal')
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState<{ ticketNum: string } | null>(null)

  const trimmed = text.trim()
  const valid = trimmed.length >= MIN_LEN && trimmed.length <= MAX_LEN
  const topicMeta = TOPICS.find((t) => t.id === topic) ?? TOPICS[0]

  const handleSubmit = () => {
    if (!valid) {
      setError(`Минимум ${MIN_LEN} символов`)
      return
    }
    setError(null)
    const prefix = `[${topicMeta.label} · ${PRIORITIES.find((p) => p.id === priority)?.label ?? ''}]\n\n`
    createFeedback.mutate(prefix + text, {
      onSuccess: (res) => {
        const ticketId = res.id ? `FB-${res.id.toString().padStart(5, '0')}` : 'FB-PENDING'
        setSubmitted({ ticketNum: ticketId })
      },
      onError: () => setError('Не удалось отправить обращение. Попробуйте позже.'),
    })
  }

  if (submitted) {
    return (
      <div className="max-w-[720px] mx-auto">
        <ScreenHeader title="Обратная связь" />
        <div className="bg-gradient-to-br from-harbor-card to-success-muted border border-success/35 rounded-2xl p-8 text-center">
          <div className="w-14 h-14 rounded-[14px] bg-success-muted text-success grid place-items-center mx-auto mb-4 shadow-[0_0_30px_rgba(var(--success-rgb),0.3)]">
            <Icon name="check" size={28} strokeWidth={2} />
          </div>
          <div className="font-display text-xl font-bold text-text-primary mb-1.5 tracking-[-0.01em]">
            Обращение отправлено
          </div>
          <div className="text-[13.5px] text-text-secondary leading-relaxed mb-[18px]">
            Номер обращения{' '}
            <span className="font-mono text-text-primary font-semibold">#{submitted.ticketNum}</span>
            .
            <br />
            Первый ответ ожидается в течение 14 минут.
          </div>
          <div className="flex gap-2 justify-center">
            <Button variant="secondary" iconLeft="feedback">
              Мои обращения
            </Button>
            <Button
              variant="primary"
              iconLeft="plus"
              onClick={() => {
                setSubmitted(null)
                setText('')
              }}
            >
              Написать ещё
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Обратная связь"
        subtitle="Опишите проблему или идею — мы прочитаем и ответим в Telegram и на почту"
        action={
          <Button variant="secondary" iconLeft="receipt" onClick={() => navigate('/feedback/my')}>
            Мои обращения
          </Button>
        }
      />

      <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(0, 1.6fr) minmax(300px, 1fr)' }}>
        <div className="bg-harbor-card border border-border rounded-xl p-[22px]">
          {error && (
            <div className="mb-4">
              <Notification type="danger">{error}</Notification>
            </div>
          )}

          <div className="mb-5">
            <Label>Тема обращения</Label>
            <div className="flex gap-2 flex-wrap">
              {TOPICS.map((t) => {
                const on = topic === t.id
                const tc = toneMap[t.tone]
                return (
                  <button
                    key={t.id}
                    onClick={() => setTopic(t.id)}
                    className={`flex items-center gap-1.5 py-2 px-3 text-[13px] font-medium rounded-lg border transition-all ${
                      on
                        ? `${tc.border} ${tc.bg} ${tc.text}`
                        : 'border-border bg-harbor-elevated text-text-secondary hover:border-border-active'
                    }`}
                  >
                    <Icon name={t.icon} size={14} />
                    {t.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="mb-5">
            <Label>Приоритет</Label>
            <div className="grid grid-cols-3 gap-2">
              {PRIORITIES.map((p) => {
                const on = priority === p.id
                return (
                  <button
                    key={p.id}
                    onClick={() => setPriority(p.id)}
                    className={`flex flex-col items-start py-2.5 px-3.5 rounded-[9px] border text-left transition-all ${
                      on
                        ? 'bg-accent-muted border-accent ring-[3px] ring-accent/15'
                        : 'bg-harbor-elevated border-border hover:border-border-active'
                    }`}
                  >
                    <div className={`text-[13px] font-semibold ${on ? 'text-accent' : 'text-text-primary'}`}>
                      {p.label}
                    </div>
                    <div className="text-[11px] text-text-tertiary mt-0.5">{p.sub}</div>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="mb-5">
            <div className="flex items-baseline justify-between">
              <Label>Описание</Label>
              <span
                className={`text-[11px] font-mono tabular-nums ${
                  text.length > MAX_LEN ? 'text-danger' : 'text-text-tertiary'
                }`}
              >
                {text.length} / {MAX_LEN}
              </span>
            </div>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Опишите ситуацию. Что вы делали? Что пошло не так? Какой результат ожидали?"
              rows={8}
              className="w-full py-3 px-3.5 bg-harbor-elevated border border-border rounded-[9px] text-text-primary font-body text-[13.5px] leading-[1.55] resize-y outline-none focus:border-accent transition-colors"
            />
            <div className="mt-2 flex gap-1.5 flex-wrap">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => setText(s)}
                  className="py-1 px-2.5 text-[11.5px] bg-transparent border border-dashed border-border rounded text-text-tertiary hover:text-accent hover:border-accent transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div
            className="flex items-center justify-between p-3.5 rounded-[9px] bg-harbor-elevated border border-border"
          >
            <div className="flex items-center gap-2.5 text-xs text-text-secondary">
              <Icon name="lock" size={14} className="text-success" />
              <span>Ваши данные защищены</span>
            </div>
            <Button
              variant="primary"
              size="md"
              loading={createFeedback.isPending}
              disabled={!valid}
              onClick={handleSubmit}
              iconRight="arrow-right"
            >
              {createFeedback.isPending ? 'Отправка…' : 'Отправить обращение'}
            </Button>
          </div>

          {!valid && text.length > 0 && text.length < MIN_LEN && (
            <div className="mt-2.5 text-xs text-warning flex items-center gap-1.5">
              <Icon name="warning" size={12} />
              Опишите ситуацию подробнее — минимум {MIN_LEN} символов (сейчас {text.length})
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3.5">
          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="flex items-center gap-2.5 mb-3.5">
              <span
                className={`w-9 h-9 rounded-[9px] grid place-items-center ${toneMap[topicMeta.tone].iconBg} ${toneMap[topicMeta.tone].iconText}`}
              >
                <Icon name={topicMeta.icon} size={16} />
              </span>
              <div>
                <div className="font-display text-sm font-semibold text-text-primary">
                  Что написать
                </div>
                <div className="text-[11.5px] text-text-tertiary mt-0.5">
                  Подсказки по теме «{topicMeta.label}»
                </div>
              </div>
            </div>

            <ul className="list-none p-0 m-0 flex flex-col gap-2.5">
              {[
                'Когда и при каких действиях это произошло',
                'Что именно пошло не так',
                'Скриншот или видео ошибки',
                'ID заявки, канала или транзакции, если есть',
              ].map((h) => (
                <li key={h} className="flex gap-2 text-[12.5px] text-text-secondary leading-[1.5]">
                  <span className="mt-0.5 w-4 h-4 rounded-full bg-accent-muted text-accent grid place-items-center flex-shrink-0">
                    <Icon name="check" size={10} strokeWidth={2.5} />
                  </span>
                  {h}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="font-display text-[13px] font-semibold text-text-primary mb-3">
              Поддержка онлайн
            </div>
            <div className="flex items-center gap-[11px] mb-3.5">
              <span className="relative w-[34px] h-[34px]">
                <span className="absolute inset-0 rounded-full bg-success opacity-25 animate-pulse" />
                <span className="absolute inset-1.5 rounded-full bg-success shadow-[0_0_10px_var(--color-success)]" />
              </span>
              <div>
                <div className="text-[13px] font-semibold text-text-primary">
                  Операторы онлайн
                </div>
                <div className="text-[11.5px] text-text-tertiary mt-px">
                  Среднее время ответа — 14 мин
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              {SIDE_CHANNELS.map((c) => (
                <a
                  key={c.title}
                  href="#"
                  className="flex items-center gap-2.5 py-2 px-2.5 rounded-[7px] bg-harbor-elevated text-text-primary hover:bg-harbor-elevated/70 transition-colors"
                >
                  <Icon name={c.icon} size={13} className="text-accent" />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12.5px] font-medium text-text-primary">{c.title}</div>
                    <div className="text-[11px] text-text-tertiary">{c.sub}</div>
                  </div>
                  <Icon name="external" size={11} className="text-text-tertiary" />
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-bold tracking-wider uppercase text-text-tertiary mb-2.5">
      {children}
    </div>
  )
}
