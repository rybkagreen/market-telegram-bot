import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { OpenInWebPortal } from '@/components/OpenInWebPortal'

/**
 * Phase 1 §1.B.2 placeholder.
 *
 * The full framework-contract flow (review, sign, KEP request) involves
 * legal profile + reqisites. ФЗ-152 forbids those in mini_app, so the
 * screen is a redirect-to-portal stub. Portal shows the same screen at
 * `/contracts/framework`.
 */
export default function AdvertiserFrameworkContract() {
  return (
    <ScreenShell>
      <Card title="Рамочный договор">
        <Text variant="md" className="mb-4">
          Подписание рамочного договора требует доступа к юридическому профилю
          и реквизитам. Согласно ФЗ-152 эти данные обрабатываются только в
          веб-портале.
        </Text>
        <OpenInWebPortal target="/contracts/framework">
          Открыть рамочный договор в портале
        </OpenInWebPortal>
      </Card>
    </ScreenShell>
  )
}
