import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { OpenInWebPortal } from '@/components/OpenInWebPortal'

/**
 * Phase 1 §1.B.2 placeholder.
 *
 * The previous mini_app implementation displayed inn / bank_account /
 * tax_regime — full PII surface. Per ФЗ-152 these fields live only in
 * the web portal at `/legal-profile/view`.
 */
export default function LegalProfileView() {
  return (
    <ScreenShell>
      <Card title="Юридический профиль">
        <Text variant="md" className="mb-4">
          Просмотр и редактирование реквизитов выполняется в веб-портале —
          согласно ФЗ-152 эти данные не передаются в мини-приложение.
        </Text>
        <OpenInWebPortal target="/legal-profile/view">
          Открыть профиль в портале
        </OpenInWebPortal>
      </Card>
    </ScreenShell>
  )
}
