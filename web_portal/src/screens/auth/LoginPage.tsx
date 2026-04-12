import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as Sentry from '@sentry/react'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@shared/api/client'
import { Card, Notification, Button } from '@shared/ui'

// ═══ Telegram Login Widget ═══
interface TelegramLoginWidgetProps {
  botName: string
  onAuth: (data: Record<string, unknown>) => void
}

function TelegramLoginWidget({ botName, onAuth }: TelegramLoginWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const onAuthRef = useRef(onAuth)

  // Keep ref updated
  useEffect(() => {
    onAuthRef.current = onAuth
  }, [onAuth])

  useEffect(() => {
    // Prevent multiple script loads
    if (containerRef.current?.hasChildNodes()) return

    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true

    const attrs: Record<string, string> = {
      'data-telegram-login': botName,
      'data-size': 'large',
      'data-onauth': 'onTelegramAuth(user)',
      'data-request-access': 'write',
      'data-radius': '12',
    }

    Object.entries(attrs).forEach(([key, value]) => {
      script.setAttribute(key, value)
    })

    // Define onTelegramAuth globally — use ref to always call latest onAuth
    ;(window as unknown as Record<string, unknown>).onTelegramAuth = (data: Record<string, unknown>) => {
      onAuthRef.current(data)
    }

    containerRef.current?.appendChild(script)

    return () => {
      delete (window as unknown as Record<string, unknown>).onTelegramAuth
      const container = containerRef.current
      if (container?.contains(script)) {
        container.removeChild(script)
      }
    }
  }, [botName])

  return <div ref={containerRef} />
}

// ═══ Login Page ═══
export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [error, setError] = useState<string | null>(null)
  const [mode, setMode] = useState<'widget' | 'code'>('widget')
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const botName = import.meta.env.VITE_BOT_USERNAME || 'RekHarborBot'

  const handleWidgetAuth = async (data: Record<string, unknown>) => {
    setError(null)
    try {
      const response = await api
        .post('auth/telegram-login-widget', { json: data })
        .json<{ access_token: string; user: Record<string, unknown> }>()

      setAuth(response.access_token, response.user as unknown as Parameters<typeof setAuth>[1])
      navigate('/')
    } catch (err) {
      Sentry.captureException(err)
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('400') || msg.includes('Invalid') || msg.includes('signature')) {
        setError('Ошибка подписи Telegram. Виджет кэширует сессию — перезагрузите страницу (Ctrl+Shift+R), убедитесь что вошли в нужный аккаунт на web.telegram.org, и попробуйте снова. Или используйте «Войти через код».')
      } else {
        setError('Не удалось войти через Telegram. Попробуйте ещё раз.')
      }
    }
  }

  const handleCodeAuth = async () => {
    if (!code.trim() || code.length !== 6) {
      setError('Введите 6-значный код')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const response = await api
        .post('auth/login-code', { json: { code: code.trim() } })
        .json<{ access_token: string; user: Record<string, unknown> }>()

      setAuth(response.access_token, response.user as unknown as Parameters<typeof setAuth>[1])
      navigate('/')
    } catch (err) {
      Sentry.captureException(err)
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('400')) {
        setError('Неверный или просроченный код. Отправьте /login боту для получения нового.')
      } else {
        setError('Не удалось войти. Попробуйте ещё раз.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-harbor-bg px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">⚓</div>
          <h1 className="text-3xl font-display font-bold text-text-primary">RekHarbor</h1>
          <p className="text-text-secondary mt-2">Рекламная биржа Telegram-каналов</p>
        </div>

        {/* Mode tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => { setMode('widget'); setError(null) }}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
              mode === 'widget'
                ? 'bg-accent text-white'
                : 'bg-harbor-elevated text-text-tertiary hover:text-text-secondary'
            }`}
          >
            📲 Telegram Login
          </button>
          <button
            onClick={() => { setMode('code'); setError(null) }}
            className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
              mode === 'code'
                ? 'bg-accent text-white'
                : 'bg-harbor-elevated text-text-tertiary hover:text-text-secondary'
            }`}
          >
            🔑 Войти через код
          </button>
        </div>

        {/* Login Card */}
        <Card title={mode === 'widget' ? 'Вход через Telegram' : 'Вход по коду'}>
          <div className="flex flex-col items-center gap-6 py-4">
            {error && (
              <Notification type="danger">
                <span>{error}</span>
              </Notification>
            )}

            {mode === 'widget' ? (
              <>
                <div className="flex justify-center">
                  <TelegramLoginWidget botName={botName} onAuth={handleWidgetAuth} />
                </div>
                <p className="text-xs text-text-tertiary text-center">
                  Нажмите кнопку «Telegram Login» — вы будете перенаправлены
                  для авторизации через ваш аккаунт Telegram.
                </p>
                <details className="text-xs text-text-tertiary text-center w-full">
                  <summary className="cursor-pointer text-accent hover:text-accent-hover transition-colors">
                    Войти через другой аккаунт
                  </summary>
                  <div className="mt-2 p-3 bg-harbor-elevated rounded-lg text-left">
                    <p className="mb-2">Telegram запоминает последний использованный аккаунт. Для смены:</p>
                    <ol className="list-decimal list-inside space-y-1 text-text-secondary">
                      <li>Откройте Telegram Desktop / Mobile</li>
                      <li>Выйдите из текущего аккаунта (Settings → Log out)</li>
                      <li>Войдите через нужный аккаунт</li>
                      <li>Вернитесь сюда и нажмите кнопку «Telegram Login»</li>
                    </ol>
                    <a
                      href="https://t.me/web"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-block mt-2 text-accent hover:text-accent-hover transition-colors"
                    >
                      → Открыть Telegram Web
                    </a>
                  </div>
                </details>
              </>
            ) : (
              <>
                <div className="w-full space-y-3">
                  <div>
                    <label className="block text-xs text-text-secondary mb-1">
                      6-значный код из бота
                    </label>
                    <input
                      type="text"
                      maxLength={6}
                      inputMode="numeric"
                      pattern="[0-9]*"
                      placeholder="123456"
                      value={code}
                      onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                      onKeyDown={(e) => e.key === 'Enter' && handleCodeAuth()}
                      className="w-full px-4 py-3 text-center text-2xl tracking-widest font-mono bg-harbor-elevated border border-border rounded-xl text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
                    />
                  </div>
                  <Button
                    variant="primary"
                    fullWidth
                    size="lg"
                    loading={submitting}
                    disabled={code.length !== 6}
                    onClick={handleCodeAuth}
                  >
                    {submitting ? '⏳ Вход...' : '✅ Войти'}
                  </Button>
                </div>
                <div className="text-xs text-text-tertiary text-center">
                  <p className="mb-2">Чтобы получить код:</p>
                  <ol className="list-decimal list-inside space-y-1 text-text-secondary">
                    <li>Откройте <a href={`https://t.me/${botName}`} target="_blank" rel="noopener noreferrer" className="text-accent hover:text-accent-hover">@{botName}</a></li>
                    <li>Отправьте команду <code className="px-1.5 py-0.5 bg-harbor-elevated rounded text-accent font-mono">/login</code></li>
                    <li>Введите полученный 6-значный код</li>
                  </ol>
                  <p className="mt-2 text-text-tertiary/70">Код действует 5 минут, используется 1 раз</p>
                </div>
              </>
            )}
          </div>
        </Card>

        {/* Footer */}
        <div className="text-center mt-8">
          <a
            href={`https://t.me/${botName}`}
            className="text-sm text-accent hover:text-accent-hover transition-colors"
          >
            Открыть бота в Telegram →
          </a>
        </div>
      </div>
    </div>
  )
}
