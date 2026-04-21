import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  EmptyState,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import { useMyLegalProfile } from '@/hooks/useLegalProfileQueries'

const FIELD_LABELS: Record<string, string> = {
  legal_name: 'Название / ФИО',
  inn: 'ИНН',
  kpp: 'КПП',
  ogrn: 'ОГРН',
  ogrnip: 'ОГРНИП',
  address: 'Адрес',
  tax_regime: 'Налоговый режим',
  bank_name: 'Банк',
  bank_account: 'Расчётный счёт',
  bank_bik: 'БИК',
  bank_corr_account: 'Корр. счёт',
}

const STATUS_LABELS: Record<string, string> = {
  individual: 'Физическое лицо',
  self_employed: 'Самозанятый',
  individual_entrepreneur: 'Индивидуальный предприниматель',
  legal_entity: 'Юридическое лицо',
}

function FieldRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border last:border-0 gap-3">
      <span className="text-[13px] text-text-secondary">{label}</span>
      <span className="text-[13px] font-mono tabular-nums text-text-primary text-right truncate">
        {value}
      </span>
    </div>
  )
}

export default function LegalProfileView() {
  const navigate = useNavigate()
  const { data: profile, isLoading } = useMyLegalProfile()

  if (isLoading) {
    return (
      <div className="max-w-[1000px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-48" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="max-w-[1000px] mx-auto">
        <ScreenHeader
          title="Юридический профиль"
        />
        <EmptyState
          icon="contract"
          title="Профиль не заполнен"
          description="Заполните юридический профиль для работы с договорами и выплатами."
          action={{
            label: 'Заполнить профиль',
            onClick: () => navigate('/legal-profile'),
          }}
        />
      </div>
    )
  }

  return (
    <div className="max-w-[1000px] mx-auto">
      <ScreenHeader
        title="Юридический профиль"
        subtitle={STATUS_LABELS[profile.legal_status] ?? profile.legal_status}
        action={
          <Button
            variant="secondary"
            size="sm"
            iconLeft="edit"
            onClick={() => navigate('/legal-profile')}
          >
            Редактировать
          </Button>
        }
      />

      <div className="flex flex-wrap gap-2 mb-5">
        {profile.is_verified && (
          <span className="inline-flex items-center gap-1.5 py-1 px-2 rounded bg-success-muted text-success text-[10.5px] font-bold tracking-[0.08em] uppercase">
            <Icon name="verified" size={12} variant="fill" />
            Верифицирован
          </span>
        )}
        {profile.has_passport_data && (
          <span className="inline-flex items-center gap-1.5 py-1 px-2 rounded bg-info-muted text-info text-[10.5px] font-bold tracking-[0.08em] uppercase">
            <Icon name="passport" size={12} />
            Паспорт добавлен
          </span>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard icon="contract" title="Основные данные">
          <div>
            <FieldRow
              label="Статус"
              value={STATUS_LABELS[profile.legal_status] ?? profile.legal_status}
            />
            <FieldRow label={FIELD_LABELS.legal_name} value={profile.legal_name} />
            <FieldRow label={FIELD_LABELS.inn} value={profile.inn} />
            <FieldRow label={FIELD_LABELS.kpp} value={profile.kpp} />
            <FieldRow label={FIELD_LABELS.ogrn} value={profile.ogrn} />
            <FieldRow label={FIELD_LABELS.ogrnip} value={profile.ogrnip} />
            <FieldRow label={FIELD_LABELS.address} value={profile.address} />
            <FieldRow label={FIELD_LABELS.tax_regime} value={profile.tax_regime} />
          </div>
        </SectionCard>

        {(profile.bank_name || profile.bank_account) && (
          <SectionCard icon="bank" title="Платёжные реквизиты">
            <div>
              <FieldRow label={FIELD_LABELS.bank_name} value={profile.bank_name} />
              <FieldRow label={FIELD_LABELS.bank_account} value={profile.bank_account} />
              <FieldRow label={FIELD_LABELS.bank_bik} value={profile.bank_bik} />
              <FieldRow label={FIELD_LABELS.bank_corr_account} value={profile.bank_corr_account} />
            </div>
          </SectionCard>
        )}
      </div>

      <div className="mt-5 flex flex-col sm:flex-row gap-3">
        <Button
          variant="primary"
          iconLeft="contract"
          className="flex-1 sm:flex-none"
          onClick={() => navigate('/contracts')}
        >
          Мои договоры
        </Button>
        <Button
          variant="secondary"
          iconLeft="upload"
          onClick={() => navigate('/legal-profile/documents')}
        >
          Загрузить документ для проверки
        </Button>
      </div>
    </div>
  )
}

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: 'contract' | 'bank'
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center gap-2">
        <Icon name={icon} size={14} className="text-text-tertiary" />
        <span className="font-display text-[14px] font-semibold text-text-primary">{title}</span>
      </div>
      <div className="px-5">{children}</div>
    </div>
  )
}
