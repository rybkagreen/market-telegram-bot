import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Button, Skeleton, EmptyState, StatusPill } from '@/components/ui'
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
  yoomoney_wallet: 'ЮMoney',
}

export default function LegalProfileView() {
  const navigate = useNavigate()
  const { data: profile, isLoading } = useMyLegalProfile()

  if (isLoading) {
    return (
      <ScreenShell>
        <Skeleton height={200} />
      </ScreenShell>
    )
  }

  if (!profile) {
    return (
      <ScreenShell>
        <EmptyState
          icon="📋"
          title="Профиль не заполнен"
          description="Заполните юридический профиль для работы с договорами и выплатами"
        />
        <Button variant="primary" fullWidth onClick={() => navigate('/legal-profile')}>
          Заполнить профиль
        </Button>
      </ScreenShell>
    )
  }

  const mainFields = ['legal_name', 'inn', 'kpp', 'ogrn', 'ogrnip', 'address', 'tax_regime'] as const
  const bankFields = ['bank_name', 'bank_account', 'bank_bik', 'bank_corr_account', 'yoomoney_wallet'] as const

  return (
    <ScreenShell>
      {profile.is_verified && (
        <div style={{ marginBottom: 8 }}>
          <StatusPill status="success">✅ Верифицирован</StatusPill>
        </div>
      )}

      <Card title="Основные данные">
        {mainFields.map((key) => {
          const val = profile[key]
          if (!val) return null
          return (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 'var(--rh-text-sm, 14px)' }}>
              <span style={{ color: 'var(--rh-text-muted)' }}>{FIELD_LABELS[key] ?? key}</span>
              <span>{String(val)}</span>
            </div>
          )
        })}
      </Card>

      <Card title="Платёжные реквизиты">
        {bankFields.map((key) => {
          const val = profile[key]
          if (!val) return null
          return (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: 'var(--rh-text-sm, 14px)' }}>
              <span style={{ color: 'var(--rh-text-muted)' }}>{FIELD_LABELS[key] ?? key}</span>
              <span>{String(val)}</span>
            </div>
          )
        })}
      </Card>

      <Card title="Документы">
        {[
          { key: 'has_inn_scan', label: 'Скан ИНН' },
          { key: 'has_passport_scan', label: 'Скан паспорта' },
          { key: 'has_self_employed_cert', label: 'Справка самозанятого' },
          { key: 'has_company_doc', label: 'Учредительные документы' },
        ].map(({ key, label }) => (
          <div key={key} style={{ display: 'flex', gap: 8, marginBottom: 6, fontSize: 'var(--rh-text-sm, 14px)' }}>
            <span>{profile[key as keyof typeof profile] ? '✅' : '⬜'}</span>
            <span style={{ color: profile[key as keyof typeof profile] ? 'inherit' : 'var(--rh-text-muted)' }}>{label}</span>
          </div>
        ))}
      </Card>

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <Button variant="secondary" fullWidth onClick={() => navigate('/legal-profile')}>
          Редактировать
        </Button>
        <Button variant="primary" fullWidth onClick={() => navigate('/contracts')}>
          Мои договоры
        </Button>
      </div>
    </ScreenShell>
  )
}
