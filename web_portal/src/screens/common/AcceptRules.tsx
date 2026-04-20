import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Notification, Skeleton, Icon, ScreenHeader } from '@shared/ui'
import { usePlatformRules, useAcceptRules } from '@/hooks/useContractQueries'

const TOC_SECTIONS = [
  { id: 'general', title: '1. Общие положения' },
  { id: 'registration', title: '2. Регистрация и верификация' },
  { id: 'payments', title: '3. Оплата и эскроу' },
  { id: 'restricted', title: '4. Запрещённые тематики' },
  { id: 'disputes', title: '5. Разрешение споров' },
  { id: 'liability', title: '6. Ответственность сторон' },
  { id: 'changes', title: '7. Изменение Правил' },
]

export default function AcceptRules() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [agreed, setAgreed] = useState<{ rules: boolean; privacy: boolean; data: boolean }>({
    rules: false,
    privacy: false,
    data: false,
  })
  const [scrolled, setScrolled] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const { data: rulesData, isLoading: viewerLoading, isError: rulesError } = usePlatformRules()
  const acceptRulesMutation = useAcceptRules()

  const viewerHtml = useMemo(() => {
    if (rulesError) {
      return '<p style="color:var(--color-danger)">Не удалось загрузить текст правил. Попробуйте позже.</p>'
    }
    if (!rulesData) return ''
    let html = rulesData.html
    html = html.replace(/<html[^>]*>/gi, '').replace(/<\/html>/gi, '')
    html = html.replace(/<head>[\s\S]*?<\/head>/gi, '')
    html = html.replace(/<body[^>]*>/gi, '').replace(/<\/body>/gi, '')
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['p', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'br', 'a', 'b', 'i', 'u'],
      ALLOWED_ATTR: ['href', 'class'],
    })
  }, [rulesData, rulesError])

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 60
    if (nearBottom) setScrolled(true)
  }

  const allAgreed = agreed.rules && agreed.privacy && agreed.data
  const canSign = allAgreed && scrolled

  const handleAccept = () => {
    if (!canSign) return
    setError(null)
    acceptRulesMutation.mutate(undefined, {
      onSuccess: async () => {
        await qc.invalidateQueries({ queryKey: ['user', 'me'] })
        await qc.refetchQueries({ queryKey: ['user', 'me'] })
        navigate('/cabinet', { replace: true })
      },
      onError: () => setError('Ошибка при принятии правил'),
    })
  }

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title="Правила платформы RekHarbor"
        subtitle="Прочитайте и подтвердите согласие — это требуется однократно"
        action={
          <Button variant="ghost" iconLeft="external">
            Скачать PDF
          </Button>
        }
      />

      {error && (
        <div className="mb-4">
          <Notification type="danger">{error}</Notification>
        </div>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: '220px minmax(0, 1fr)' }}>
        <nav className="bg-harbor-card border border-border rounded-xl p-3.5 sticky top-5 self-start max-h-[calc(100vh-140px)]">
          <div className="text-[10.5px] font-bold tracking-[0.08em] uppercase text-text-tertiary py-1 px-2 pb-2.5">
            Содержание
          </div>
          <ul className="list-none p-0 m-0 flex flex-col gap-0.5">
            {TOC_SECTIONS.map((s) => (
              <li key={s.id}>
                <button
                  className="w-full text-left py-2 px-2.5 rounded-md bg-transparent text-text-secondary text-[12.5px] font-medium hover:bg-harbor-elevated hover:text-text-primary transition-colors"
                >
                  {s.title}
                </button>
              </li>
            ))}
          </ul>

          <div
            className={`mt-3.5 p-2.5 rounded-[7px] text-[11.5px] flex items-center gap-2 ${
              scrolled ? 'bg-success-muted text-success' : 'bg-harbor-elevated text-text-tertiary'
            }`}
          >
            <Icon name={scrolled ? 'check' : 'clock'} size={12} strokeWidth={2} />
            {scrolled ? 'Прочитано до конца' : 'Дочитайте до конца'}
          </div>
        </nav>

        <div className="flex flex-col gap-4">
          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="bg-harbor-card border border-border rounded-xl py-[22px] px-7 max-h-[520px] overflow-y-auto scrollbar-thin"
          >
            <div className="text-[11px] font-bold tracking-[0.08em] uppercase text-text-tertiary mb-1.5">
              Редакция 3.2 · действует с 15 апреля 2026
            </div>
            <h2 className="font-display text-xl font-bold text-text-primary mb-[18px] tracking-[-0.015em]">
              Правила использования платформы
            </h2>

            {viewerLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-4 w-4/6" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            ) : (
              <div
                className="prose prose-invert prose-sm max-w-none prose-headings:text-text-primary prose-p:text-text-secondary prose-strong:text-text-primary prose-a:text-accent prose-li:text-text-secondary"
                dangerouslySetInnerHTML={{ __html: viewerHtml }}
              />
            )}

            <div className="mt-6 p-3.5 rounded-[9px] bg-accent-muted border border-accent/15 flex gap-2.5 items-start">
              <Icon name="info" size={14} className="text-accent mt-0.5 flex-shrink-0" />
              <div className="text-[12.5px] text-text-secondary leading-[1.5]">
                Полный текст актуальной редакции, историю изменений и Политику конфиденциальности вы можете скачать в PDF на этой же странице.
              </div>
            </div>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5 flex flex-col gap-3">
            {[
              {
                id: 'rules' as const,
                text: (
                  <>
                    Я прочитал(а) и согласен(-на) с <span className="text-accent">Правилами платформы</span> и{' '}
                    <span className="text-accent">Публичной офертой</span>
                  </>
                ),
              },
              {
                id: 'privacy' as const,
                text: (
                  <>
                    Согласен(-на) на обработку персональных данных согласно{' '}
                    <span className="text-accent">Политике конфиденциальности</span>
                  </>
                ),
              },
              {
                id: 'data' as const,
                text: <>Согласен(-на) получать информационные сообщения о статусах кампаний и выплатах</>,
              },
            ].map((c) => (
              <label key={c.id} className="flex gap-3 items-start cursor-pointer">
                <button
                  type="button"
                  onClick={() => setAgreed((prev) => ({ ...prev, [c.id]: !prev[c.id] }))}
                  className={`w-5 h-5 rounded-[5px] grid place-items-center border-[1.5px] p-0 text-white flex-shrink-0 mt-px transition-colors ${
                    agreed[c.id] ? 'bg-accent border-accent' : 'bg-harbor-elevated border-border'
                  }`}
                >
                  {agreed[c.id] && <Icon name="check" size={12} strokeWidth={2.5} />}
                </button>
                <span className="text-[13px] text-text-primary leading-[1.5]">{c.text}</span>
              </label>
            ))}
          </div>

          <div className="flex items-center justify-between flex-wrap gap-3 p-3.5 rounded-[10px] bg-harbor-elevated border border-border">
            <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
              <Icon name="lock" size={14} className="text-success" />
              <span>
                Подписание простой электронной подписью · юридически равнозначно бумажной
              </span>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => navigate('/cabinet')}>
                Отклонить
              </Button>
              <Button
                variant="primary"
                disabled={!canSign}
                loading={acceptRulesMutation.isPending}
                iconRight="arrow-right"
                onClick={handleAccept}
              >
                Принять и подписать
              </Button>
            </div>
          </div>

          {!canSign && (
            <div className="text-xs text-text-tertiary flex gap-1.5 items-center justify-center">
              <Icon name="info" size={12} />
              {!scrolled
                ? 'Дочитайте текст до конца, чтобы активировать кнопку'
                : 'Отметьте все обязательные согласия'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
