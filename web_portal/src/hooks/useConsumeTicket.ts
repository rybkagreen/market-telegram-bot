import { useMutation } from '@tanstack/react-query'
import { consumeTicket } from '@/api/auth'

/**
 * Phase 1 §1.B.3 — bridge ticket consumption.
 *
 * `TicketLogin` calls this after extracting `?ticket=` from the URL. On success
 * the access_token is in the response; the screen writes it to localStorage,
 * fetches `/api/auth/me` to populate the auth store user object, then navigates
 * to `redirect` (after `safeRedirect` validation).
 *
 * No `onSuccess` here — token persistence + redirect are screen concerns and
 * react-router-dom hooks (`useNavigate`) belong in the screen, not the hook.
 */
export function useConsumeTicket() {
  return useMutation({
    mutationFn: (ticket: string) => consumeTicket(ticket),
  })
}
