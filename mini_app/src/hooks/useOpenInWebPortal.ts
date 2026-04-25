import { useMutation } from '@tanstack/react-query'
import { exchangeMiniappToPortal } from '@/api/auth'
import { useUiStore } from '@/stores/uiStore'

/**
 * Phase 1 §1.B.3 — bridge from mini_app to web_portal.
 *
 * Calls `/api/auth/exchange-miniapp-to-portal` to mint a short-lived ticket,
 * then opens `${portal_url}/login/ticket?ticket=...&redirect=<target>` in the
 * external browser via `Telegram.WebApp.openLink`. After mounting in the
 * portal's `TicketLogin` screen the user lands on `<target>` authenticated.
 *
 * `target` MUST be a same-origin path starting with a single `/` — the portal
 * `safeRedirect` rejects anything else and falls back to `/cabinet`.
 */
export function useOpenInWebPortal(target: string) {
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: exchangeMiniappToPortal,
    onSuccess: (data) => {
      const url = `${data.portal_url}/login/ticket?ticket=${encodeURIComponent(
        data.ticket,
      )}&redirect=${encodeURIComponent(target)}`
      // Telegram.WebApp.openLink leaves the WebApp on iOS/Android; falls back
      // to window.open for desktop Telegram and unit-test harnesses.
      if (window.Telegram?.WebApp?.openLink) {
        window.Telegram.WebApp.openLink(url)
      } else {
        window.open(url, '_blank')
      }
    },
    onError: () => {
      addToast('error', 'Не удалось открыть портал. Попробуйте ещё раз.')
    },
  })
}
