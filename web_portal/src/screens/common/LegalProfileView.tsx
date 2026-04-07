import { useNavigate } from 'react-router-dom'
import { Card, Button, Skeleton, EmptyState, StatusPill } from '@shared/ui'
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
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-text-secondary">{label}</span>
      <span className="text-sm font-mono text-text-primary">{value}</span>
    </div>
  )
}

export default function LegalProfileView() {
  const navigate = useNavigate()
  const { data: profile, isLoading } = useMyLegalProfile()

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-32" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="space-y-4">
        <EmptyState icon="📋" title="Профиль не заполнен" description="Заполните юридический профиль для работы с договорами и выплатами" />
        <Button variant="primary" fullWidth onClick={() => navigate('/legal-profile')}>
          Заполнить профиль
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Юридический профиль</h1>

      {profile.is_verified && (
        <StatusPill status="success">✅ Верифицирован</StatusPill>
      )}

      <Card title="Основные данные">
        <div className="divide-y divide-border">
          <FieldRow label="Статус" value={STATUS_LABELS[profile.legal_status] ?? profile.legal_status} />
          <FieldRow label={FIELD_LABELS.legal_name} value={profile.legal_name} />
          <FieldRow label={FIELD_LABELS.inn} value={profile.inn} />
          <FieldRow label={FIELD_LABELS.kpp} value={profile.kpp} />
          <FieldRow label={FIELD_LABELS.ogrn} value={profile.ogrn} />
          <FieldRow label={FIELD_LABELS.ogrnip} value={profile.ogrnip} />
          <FieldRow label={FIELD_LABELS.address} value={profile.address} />
          <FieldRow label={FIELD_LABELS.tax_regime} value={profile.tax_regime} />
        </div>
      </Card>

      {(profile.bank_name || profile.bank_account) && (
        <Card title="Платёжные реквизиты">
          <div className="divide-y divide-border">
            <FieldRow label={FIELD_LABELS.bank_name} value={profile.bank_name} />
            <FieldRow label={FIELD_LABELS.bank_account} value={profile.bank_account} />
            <FieldRow label={FIELD_LABELS.bank_bik} value={profile.bank_bik} />
            <FieldRow label={FIELD_LABELS.bank_corr_account} value={profile.bank_corr_account} />
          </div>
        </Card>
      )}

      <div className="space-y-3">
        <Button variant="secondary" fullWidth onClick={() => navigate('/legal-profile')}>
          Редактировать
        </Button>
        <Button variant="ghost" fullWidth onClick={() => navigate('/legal-profile/documents')}>
          📸 Загрузить документ для проверки
        </Button>
        <Button variant="primary" fullWidth onClick={() => navigate('/contracts')}>
          📄 Мои договоры
        </Button>
      </div>
    </div>
  )
}
