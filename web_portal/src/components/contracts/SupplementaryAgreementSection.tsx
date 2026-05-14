import { useQueryClient } from '@tanstack/react-query'
import { Button, Notification, Skeleton, Icon } from '@shared/ui'
import {
  useSupplementaryAgreement,
  useSignContract,
} from '@/hooks/useContractQueries'
import type { Contract, ContractRole } from '@/lib/types/contracts'

interface SupplementaryAgreementSectionProps {
  placementId: number
  role: ContractRole
}

const COUNTERPARTY_LABEL: Record<ContractRole, string> = {
  advertiser: 'владельца канала',
  owner: 'рекламодателя',
}

export function SupplementaryAgreementSection({
  placementId,
  role,
}: SupplementaryAgreementSectionProps) {
  const queryClient = useQueryClient()
  const { data, isLoading, isError, error } = useSupplementaryAgreement(placementId)
  const signMutation = useSignContract()

  if (isLoading) {
    return (
      <div className="bg-harbor-card border border-border rounded-xl p-5">
        <Skeleton className="h-6 mb-3" />
        <Skeleton className="h-20" />
      </div>
    )
  }

  if (isError) {
    const status = (error as { response?: { status?: number } } | undefined)?.response?.status
    if (status === 404) return null
    return (
      <div className="bg-harbor-card border border-border rounded-xl p-5">
        <Notification type="danger">
          Не удалось загрузить доп. соглашение. Обновите страницу.
        </Notification>
      </div>
    )
  }

  if (!data) return null

  const ownSide: Contract = role === 'advertiser' ? data.advertiser : data.owner
  const otherSide: Contract = role === 'advertiser' ? data.owner : data.advertiser
  const ownSigned = ownSide.contract_status === 'signed'
  const otherSigned = otherSide.contract_status === 'signed'
  const signing = signMutation.isPending

  const handleSign = () => {
    signMutation.mutate(
      { id: ownSide.id, method: 'button_accept' },
      {
        onSuccess: () => {
          queryClient.invalidateQueries({
            queryKey: ['supplementary-agreement', placementId],
          })
        },
      },
    )
  }

  return (
    <div className="bg-harbor-card border border-border rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3">
        <Icon name="docs" size={14} className="text-accent" />
        <h3 className="font-display text-[14px] font-semibold text-text-primary">
          Доп. соглашение по этой заявке
        </h3>
      </div>

      {data.both_signed ? (
        <Notification type="success">
          ДС подписано обеими сторонами. Заявка готова к оплате.
        </Notification>
      ) : (
        <p className="text-[13px] text-text-secondary leading-[1.5] mb-3">
          Перед оплатой стороны подписывают доп. соглашение, фиксирующее условия
          этого размещения (канал, цена, формат, дата, текст РИМ).
        </p>
      )}

      <div className="mt-3 grid gap-2.5 text-[13px]">
        <SideStatus
          label="Ваша сторона"
          signed={ownSigned}
          pdfUrl={ownSide.pdf_url}
        />
        <SideStatus
          label={`Сторона ${COUNTERPARTY_LABEL[role]}`}
          signed={otherSigned}
          pdfUrl={otherSide.pdf_url}
        />
      </div>

      {!ownSigned && (
        <div className="mt-4 border-t border-border pt-4">
          <Button
            variant="primary"
            iconLeft="check"
            fullWidth
            loading={signing}
            onClick={handleSign}
          >
            Подписать ДС
          </Button>
          {signMutation.isError && (
            <p className="text-[12px] text-danger mt-2">
              Не удалось подписать. Попробуйте ещё раз.
            </p>
          )}
        </div>
      )}

      {ownSigned && !otherSigned && (
        <p className="text-[12px] text-text-tertiary mt-3">
          Вы подписали ДС. Ожидается подпись {COUNTERPARTY_LABEL[role]}.
        </p>
      )}
    </div>
  )
}

function SideStatus({
  label,
  signed,
  pdfUrl,
}: {
  label: string
  signed: boolean
  pdfUrl: string | null
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-text-secondary">{label}</span>
      <span className="flex items-center gap-2">
        {pdfUrl && (
          <a
            href={`/api/${pdfUrl.replace(/^\/api\//, '')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[12px] text-accent hover:text-accent-hover"
          >
            PDF
          </a>
        )}
        <span
          className={`text-[11px] font-semibold tracking-[0.06em] uppercase px-2 py-0.5 rounded ${
            signed
              ? 'bg-success-muted text-success'
              : 'bg-warning-muted text-warning'
          }`}
        >
          {signed ? 'Подписано' : 'Ожидает'}
        </span>
      </span>
    </div>
  )
}
