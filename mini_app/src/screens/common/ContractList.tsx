import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Skeleton, EmptyState } from '@/components/ui'
import { ContractCard } from '@/components/ContractCard'
import { useContracts } from '@/hooks/useContractQueries'

export default function ContractList() {
  const navigate = useNavigate()
  const { data, isLoading } = useContracts()

  return (
    <ScreenShell>
      <p style={{ fontWeight: 700, fontSize: 'var(--rh-text-lg, 18px)', marginBottom: 16 }}>
        Мои договоры
      </p>

      {isLoading ? (
        <>
          <Skeleton height={100} />
          <Skeleton height={100} />
        </>
      ) : !data?.items.length ? (
        <EmptyState icon="📄" title="Договоров пока нет" description="Договоры появятся после начала работы на платформе" />
      ) : (
        data.items.map((contract) => (
          <ContractCard
            key={contract.id}
            contract={contract}
            onView={() => navigate(`/contracts/${contract.id}`)}
            onSign={() => navigate(`/contracts/${contract.id}`)}
          />
        ))
      )}
    </ScreenShell>
  )
}
