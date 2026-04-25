import { useParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card } from '@/components/ui'
import { Text } from '@/components/ui/Text'
import { OpenInWebPortal } from '@/components/OpenInWebPortal'

/**
 * Phase 1 §1.B.2 placeholder.
 *
 * Campaign payment touches the framework-contract gate and surfaces fee
 * breakdowns sourced from the legal profile. Per ФЗ-152 + the user's
 * heavy-strip decision (option A), the full payment flow lives only in the
 * web portal at `/adv/campaigns/:id/payment`.
 */
export default function CampaignPayment() {
  const { id } = useParams<{ id: string }>()
  const target = id ? `/adv/campaigns/${id}/payment` : '/adv/campaigns'

  return (
    <ScreenShell>
      <Card title="Оплата кампании">
        <Text variant="md" className="mb-4">
          Оплата требует проверки рамочного договора и доступа к реквизитам.
          Согласно ФЗ-152 эти данные обрабатываются только в веб-портале.
        </Text>
        <OpenInWebPortal target={target}>
          Перейти к оплате в портале
        </OpenInWebPortal>
      </Card>
    </ScreenShell>
  )
}
