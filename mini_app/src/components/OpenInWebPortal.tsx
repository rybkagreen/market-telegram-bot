import type { ReactNode } from 'react'
import { Button } from '@/components/ui'
import { useOpenInWebPortal } from '@/hooks/useOpenInWebPortal'

interface OpenInWebPortalProps {
  /** Same-origin path starting with `/` — e.g. `/legal-profile`, `/contracts`. */
  target: string
  /** Custom button label. Defaults to "Открыть в портале". */
  children?: ReactNode
  /** Optional className passthrough for layout (e.g. `w-full`). */
  className?: string
}

/**
 * Phase 1 §1.B.3 — bridge UI affordance.
 *
 * Renders a button that, on click, mints a portal ticket and opens
 * `${portal_url}/login/ticket?ticket=...&redirect=<target>` via
 * `Telegram.WebApp.openLink`. After Phase 1 §1.B.2 (mini_app legal strip),
 * every PII flow that used to render a screen here is replaced with this
 * component pointing at the corresponding portal route.
 *
 * Loading / error UX is handled by the hook (toasts on error). Component
 * just wires the click + label.
 */
export function OpenInWebPortal({ target, children, className }: OpenInWebPortalProps) {
  const { mutate, isPending } = useOpenInWebPortal(target)

  return (
    <Button
      onClick={() => mutate()}
      disabled={isPending}
      className={className}
    >
      {isPending ? 'Открываем…' : (children ?? 'Открыть в портале')}
    </Button>
  )
}
