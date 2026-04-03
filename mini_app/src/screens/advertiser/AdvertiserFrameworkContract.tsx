import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Skeleton, Notification, Button, Text } from '@/components/ui'
import { ContractCard } from '@/components/ContractCard'
import { KepWarning } from '@/components/KepWarning'
import {
  useContracts,
  useGenerateContract,
  useSignContract,
} from '@/hooks/useContractQueries'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'
import type { LegalStatus } from '@/lib/types'
import styles from './AdvertiserFrameworkContract.module.css'

const SIGN_BUTTON_LABEL: Record<LegalStatus, string> = {
  individual: '✅ Подписать',
  self_employed: '✅ Подписать',
  individual_entrepreneur: '✅ Подписать (ПЭП)',
  legal_entity: '✅ Подписать (ПЭП — ознакомлен с ограничениями)',
}

export default function AdvertiserFrameworkContract() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnTo = searchParams.get('returnTo') ?? '/adv'
  const [signed, setSigned] = useState(false)

  const { data: contractsList, isLoading: listLoading } = useContracts('advertiser_framework')
  const { mutate: generateContract, data: generatedContract, isPending: generating } = useGenerateContract()
  const { mutate: signContract, isPending: signing } = useSignContract()
  const { data: profile } = useMyLegalProfile()

  const legalStatus: LegalStatus = (profile?.legal_status as LegalStatus) ?? 'individual'

  // Check if already signed — redirect immediately
  useEffect(() => {
    if (!listLoading && contractsList) {
      const alreadySigned = contractsList.items.find(
        (c) => c.contract_type === 'advertiser_framework' && c.contract_status === 'signed',
      )
      if (alreadySigned) {
        navigate(returnTo, { replace: true })
      }
    }
  }, [contractsList, listLoading, navigate, returnTo])

  // Generate framework contract on mount if not already present
  useEffect(() => {
    if (!listLoading && contractsList && contractsList.items.length === 0) {
      generateContract({ contractType: 'advertiser_framework' })
    }
  }, [contractsList, listLoading, generateContract])

  // Determine the contract to show
  const existingDraft = contractsList?.items.find(
    (c) => c.contract_type === 'advertiser_framework' && c.contract_status !== 'signed',
  )
  const contract = existingDraft ?? generatedContract

  const handleSign = () => {
    if (!contract) return
    signContract(
      { id: contract.id, method: 'button_accept' },
      {
        onSuccess: () => {
          setSigned(true)
          setTimeout(() => navigate(returnTo, { replace: true }), 1500)
        },
      },
    )
  }

  if (listLoading || generating) {
    return (
      <ScreenShell>
        <Skeleton height={80} />
        <Skeleton height={150} />
      </ScreenShell>
    )
  }

  const signLabel = SIGN_BUTTON_LABEL[legalStatus] ?? '✅ Подписать'

  return (
    <ScreenShell>
      <Text variant="lg" weight="bold" font="display" className={styles.title}>
        Рамочный договор на размещение рекламы
      </Text>
      <Text variant="sm" color="muted" className={styles.subtitle}>
        Этот договор подписывается один раз и охватывает все ваши рекламные кампании на платформе.
      </Text>

      {contract && (
        <>
          <ContractCard contract={contract} legalStatus={legalStatus} />
          <KepWarning contract={contract} legalStatus={legalStatus} />
        </>
      )}

      {signed ? (
        <Notification type="success">
          ✅ Договор подписан. Переходим к оплате...
        </Notification>
      ) : contract ? (
        <div className={styles.signSection}>
          <Button variant="primary" fullWidth disabled={signing} onClick={handleSign}>
            {signing ? '⏳ Подписание...' : signLabel}
          </Button>
        </div>
      ) : (
        <Notification type="warning">Не удалось загрузить договор. Попробуйте позже.</Notification>
      )}
    </ScreenShell>
  )
}
