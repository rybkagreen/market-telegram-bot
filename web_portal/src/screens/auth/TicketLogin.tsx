import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import * as Sentry from '@sentry/react'
import { useAuthStore } from '@/stores/authStore'
import { useConsumeTicket } from '@/hooks/useConsumeTicket'
import { getMe } from '@/api/auth'
import { Card, Notification, Button } from '@shared/ui'

/**
 * Phase 1 §1.B.3 — bridge landing.
 *
 * Reachable as `${portal_url}/login/ticket?ticket=<jwt>&redirect=/legal-profile`.
 * Mini_app's `OpenInWebPortal` constructs the URL after calling
 * `/api/auth/exchange-miniapp-to-portal`. Here we:
 *   1. Validate `redirect` is same-origin (open-redirect guard, see safeRedirect).
 *   2. Consume the ticket → web_portal access_token.
 *   3. Persist token (localStorage so ky's beforeRequest hook can attach it).
 *   4. Fetch /api/auth/me to populate the User object in zustand.
 *   5. Navigate to the validated redirect (default '/cabinet').
 */

/**
 * Allowlist redirect: only same-origin relative paths starting with a single
 * `/`. Blocks `https://evil.com`, `//evil.com`, `javascript:`, and any other
 * URL-shape attacker can pass via `?redirect=`. Failing → '/cabinet'.
 *
 * Tested in `web_portal/tests/specs/ticket-login.spec.ts`.
 */
function safeRedirect(raw: string | null): string {
  if (!raw) return '/cabinet'
  // Must start with single `/`, not `//` (protocol-relative).
  if (!/^\/[^/]/.test(raw)) return '/cabinet'
  return raw
}

export default function TicketLogin() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { setAuth } = useAuthStore()
  const consume = useConsumeTicket()
  const [error, setError] = useState<string | null>(null)
  const ranRef = useRef(false)

  const ticket = searchParams.get('ticket')
  const redirect = safeRedirect(searchParams.get('redirect'))

  useEffect(() => {
    // StrictMode in dev fires effects twice; guard against double-consume
    // (the second call would 401 because the jti was already deleted).
    if (ranRef.current) return
    ranRef.current = true

    if (!ticket) {
      setError('Ссылка некорректна: отсутствует ticket. Откройте Mini App и попробуйте ещё раз.')
      return
    }

    consume.mutate(ticket, {
      onSuccess: async (data) => {
        try {
          // Step 3: persist token so ky's beforeRequest reads it for /me call.
          localStorage.setItem('rh_token', data.access_token)
          // Step 4: fetch user object — auth store needs it.
          const user = await getMe()
          setAuth(data.access_token, user)
          // Step 5: navigate to validated target.
          navigate(redirect, { replace: true })
        } catch (err) {
          Sentry.captureException(err)
          // Token was set but /me failed — clean up to avoid half-authed state.
          localStorage.removeItem('rh_token')
          setError('Сессия создана, но не удалось получить профиль. Войдите заново.')
        }
      },
      onError: (err) => {
        Sentry.captureException(err)
        const msg = err instanceof Error ? err.message : ''
        if (msg.includes('429')) {
          setError('Слишком много попыток. Подождите минуту и попробуйте ещё раз.')
        } else if (msg.includes('401')) {
          setError(
            'Ссылка устарела или уже была использована. Откройте Mini App и сгенерируйте новую.',
          )
        } else {
          setError('Не удалось войти. Попробуйте ещё раз или зайдите через /login.')
        }
      },
    })
    // Intentionally only run once on mount; ticket is captured at that moment.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-harbor-bg px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <picture>
            <source srcSet="/brand/rekharbor_full_light.svg" media="(prefers-color-scheme: light)" />
            <img
              src="/brand/rekharbor_full_dark.svg"
              alt="RekHarbor"
              width={237}
              height={48}
              className="mx-auto mb-3 h-12 w-[237px]"
            />
          </picture>
          <p className="text-text-secondary mt-2">Вход через Mini App</p>
        </div>

        <Card title={error ? 'Ошибка входа' : 'Авторизация…'}>
          <div className="flex flex-col items-center gap-6 py-4">
            {error ? (
              <>
                <Notification type="danger">
                  <span>{error}</span>
                </Notification>
                <Link to="/login">
                  <Button>Вернуться на страницу входа</Button>
                </Link>
              </>
            ) : (
              <p className="text-sm text-text-tertiary text-center">
                Проверяем ссылку и завершаем вход…
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

// Exported for unit tests covering the redirect allowlist.
export { safeRedirect }
