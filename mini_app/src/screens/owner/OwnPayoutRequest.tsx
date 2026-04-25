import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { OpenInWebPortal } from '@/components/OpenInWebPortal'

/**
 * Phase 1 §1.B.2 placeholder.
 *
 * Payout requests need bank requisites + legal profile (PII). Per ФЗ-152
 * these flows live only in the web portal. Portal screen at
 * `/own/payouts/request`.
 */
export default function OwnPayoutRequest() {
  return (
    <ScreenShell>
      <Card title="Заявка на выплату">
        <Text variant="md" className="mb-4">
          Заявки на выплату требуют реквизитов и юридического профиля.
          Согласно ФЗ-152 эти данные обрабатываются только в веб-портале.
        </Text>
        <OpenInWebPortal target="/own/payouts/request">
          Создать заявку в портале
        </OpenInWebPortal>
      </Card>
    </ScreenShell>
  )
}
