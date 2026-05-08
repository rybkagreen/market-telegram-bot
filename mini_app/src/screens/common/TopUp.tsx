import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { OpenInWebPortal } from '@/components/OpenInWebPortal'

/**
 * T1.2.5f Bundle D placeholder.
 *
 * The mini_app topup flow was retired — payment authoritative state lives
 * only in the web portal at `/topup`.
 */
export default function TopUp() {
  return (
    <ScreenShell>
      <Card title="Пополнение баланса">
        <Text variant="md" className="mb-4">
          Пополнение баланса перенесено в веб-портал. Откройте по ссылке ниже.
        </Text>
        <OpenInWebPortal target="/topup">
          Открыть веб-портал
        </OpenInWebPortal>
      </Card>
    </ScreenShell>
  )
}
