import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { useQueryClient } from '@tanstack/react-query'
import { Card, Button, Notification, Skeleton } from '@shared/ui'
import { usePlatformRules, useAcceptRules } from '@/hooks/useContractQueries'

export default function AcceptRules() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [accepted, setAccepted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { data: rulesData, isLoading: viewerLoading, isError: rulesError } = usePlatformRules()
  const acceptRulesMutation = useAcceptRules()

  const viewerHtml = useMemo(() => {
    if (rulesError) {
      return '<p style="color:#e74c3c">Не удалось загрузить текст правил. Попробуйте позже.</p>'
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

  const handleAccept = () => {
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
    <div className="space-y-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-display font-bold text-text-primary">Правила платформы</h1>

      {error && <Notification type="danger">{error}</Notification>}

      {/* Rules viewer — dark mode container */}
      <div
        className="rounded-lg overflow-hidden"
        style={{
          background: '#1a1a2e',
          color: '#e0e0e0',
          fontFamily: "'Times New Roman', Times, serif",
          fontSize: '11pt',
          lineHeight: '1.6',
          padding: '20px 30px',
          maxHeight: '60vh',
          overflowY: 'auto',
        }}
      >
        {viewerLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-4/6" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
          </div>
        ) : (
          <div
            className="prose prose-invert prose-sm max-w-none
              prose-headings:text-white prose-p:text-gray-300 prose-strong:text-white
              prose-a:text-accent prose-li:text-gray-300"
            dangerouslySetInnerHTML={{ __html: viewerHtml }}
          />
        )}
      </div>

      {/* Accept checkbox */}
      <Card>
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-1 w-5 h-5 rounded border-border-active bg-harbor-elevated text-accent
              focus:ring-accent focus:ring-2"
          />
          <span className="text-sm text-text-primary">
            Я принимаю Правила платформы и Политику конфиденциальности
          </span>
        </label>
      </Card>

      {/* Accept button */}
      <Button
        variant="primary"
        fullWidth
        size="lg"
        loading={acceptRulesMutation.isPending}
        disabled={!accepted || acceptRulesMutation.isPending}
        onClick={handleAccept}
      >
        {acceptRulesMutation.isPending ? '⏳ Принятие...' : '✅ Принять правила'}
      </Button>
    </div>
  )
}
