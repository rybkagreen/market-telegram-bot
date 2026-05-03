import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { OpenInWebPortal } from '@/components/OpenInWebPortal'

/**
 * 16.3 deeplink target — bot payout entry buttons
 * (`own_menu`, `cabinet`, post-completion notification) open
 * `WebAppInfo(url=mini_app + /own/payouts/request)`. This screen is the
 * placeholder that mints a portal ticket and redirects; payout setup
 * itself lives only in the web portal.
 *
 * Per ФЗ-152: PII (card / phone / account requisites) never travels
 * through Telegram or mini_app. The bot payout FSM was removed in 16.3
 * (BL-045 closed); BL-055 tracks a future direct bot→portal exchange
 * that would obviate this placeholder.
 *
 * Pattern: Phase 1 §1.B.2 (see also `LegalProfileView`).
 */
export default function OwnPayoutRequest() {
  return (
    <ScreenShell>
      <Card title="Запрос вывода">
        <Text variant="md" className="mb-4">
          Запрос вывода и ввод реквизитов выполняется в веб-портале —
          согласно ФЗ-152 платёжные реквизиты не передаются через
          Telegram и мини-приложение.
        </Text>
        <OpenInWebPortal target="/own/payouts/request">
          Открыть в портале
        </OpenInWebPortal>
      </Card>
    </ScreenShell>
  )
}
