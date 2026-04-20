import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Notification, Select, Textarea, Icon, ScreenHeader, StepIndicator } from '@shared/ui'
import type { IconName } from '@shared/ui'
import {
  useMyLegalProfile,
  useCreateLegalProfile,
  useUpdateLegalProfile,
  useValidateInn,
  useRequiredFields,
  useValidateEntity,
} from '@/hooks/useLegalProfileQueries'

type LegalStatus = 'individual' | 'self_employed' | 'individual_entrepreneur' | 'legal_entity'

interface LegalTypeConf {
  id: LegalStatus
  label: string
  sub: string
  icon: IconName
  tone: 'success' | 'accent' | 'accent2' | 'warning'
}

const LEGAL_TYPES: LegalTypeConf[] = [
  { id: 'self_employed', label: 'Самозанятый', sub: 'НПД, ставка 6%', icon: 'users', tone: 'success' },
  { id: 'individual_entrepreneur', label: 'ИП', sub: 'УСН / ПСН', icon: 'cabinet', tone: 'accent' },
  { id: 'legal_entity', label: 'ООО', sub: 'Юридическое лицо', icon: 'admin', tone: 'accent2' },
  { id: 'individual', label: 'Физлицо', sub: 'НДФЛ, ставка 13%', icon: 'referral', tone: 'warning' },
]

const TAX_REGIME_OPTIONS = [
  { value: 'osno', label: 'ОСНО' },
  { value: 'usn', label: 'УСН' },
  { value: 'usn_d', label: 'УСН (доходы)' },
  { value: 'usn_dr', label: 'УСН (доходы − расходы)' },
  { value: 'patent', label: 'Патент (ПСН)' },
  { value: 'npd', label: 'НПД' },
  { value: 'ndfl', label: 'НДФЛ' },
]

const toneTileClass: Record<LegalTypeConf['tone'], { border: string; bg: string; text: string; iconBg: string; iconText: string }> = {
  success: { border: 'border-success', bg: 'bg-success-muted', text: 'text-success', iconBg: 'bg-success/15', iconText: 'text-success' },
  accent: { border: 'border-accent', bg: 'bg-accent-muted', text: 'text-accent', iconBg: 'bg-accent/15', iconText: 'text-accent' },
  accent2: { border: 'border-accent-2', bg: 'bg-accent-2-muted', text: 'text-accent-2', iconBg: 'bg-accent-2/15', iconText: 'text-accent-2' },
  warning: { border: 'border-warning', bg: 'bg-warning-muted', text: 'text-warning', iconBg: 'bg-warning/15', iconText: 'text-warning' },
}

export default function LegalProfileSetup() {
  const navigate = useNavigate()
  const { data: existingProfile } = useMyLegalProfile()
  const [status, setStatus] = useState<LegalStatus | ''>('')
  const { data: requiredFields } = useRequiredFields(status || undefined)
  const createMutation = useCreateLegalProfile()
  const updateMutation = useUpdateLegalProfile()
  const innMutation = useValidateInn()
  const fnsMutation = useValidateEntity()

  const [legalName, setLegalName] = useState('')
  const [inn, setInn] = useState('')
  const [kpp, setKpp] = useState('')
  const [ogrn, setOgrn] = useState('')
  const [ogrnip, setOgrnip] = useState('')
  const [address, setAddress] = useState('')
  const [taxRegime, setTaxRegime] = useState('')
  const [bankName, setBankName] = useState('')
  const [bankAccount, setBankAccount] = useState('')
  const [bankBik, setBankBik] = useState('')
  const [bankCorrAccount, setBankCorrAccount] = useState('')
  const [yoomoneyWallet, setYoomoneyWallet] = useState('')
  const [passportSeries, setPassportSeries] = useState('')
  const [passportNumber, setPassportNumber] = useState('')
  const [passportIssuedBy, setPassportIssuedBy] = useState('')
  const [passportIssuedAt, setPassportIssuedAt] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [fnsResult, setFnsResult] = useState<{
    is_valid: boolean
    warnings: string[]
    errors: { field: string; message: string }[]
  } | null>(null)

  const fields = requiredFields?.fields ?? []
  const isLegalEntity = status === 'legal_entity'
  const isIE = status === 'individual_entrepreneur'
  const isSelfEmployed = status === 'self_employed'
  const isIndividual = status === 'individual'
  const showBank = isLegalEntity || isIE

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (existingProfile) {
      setStatus(existingProfile.legal_status as LegalStatus)
      setLegalName(existingProfile.legal_name ?? '')
      setInn(existingProfile.inn ?? '')
      setKpp(existingProfile.kpp ?? '')
      setOgrn(existingProfile.ogrn ?? '')
      setOgrnip(existingProfile.ogrnip ?? '')
      setAddress(existingProfile.address ?? '')
      setTaxRegime(existingProfile.tax_regime ?? '')
      setBankName(existingProfile.bank_name ?? '')
      setBankAccount(existingProfile.bank_account ?? '')
      setBankBik(existingProfile.bank_bik ?? '')
      setBankCorrAccount(existingProfile.bank_corr_account ?? '')
      setYoomoneyWallet(existingProfile.yoomoney_wallet ?? '')
    }
  }, [existingProfile])
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleValidate = () => {
    if (!inn) {
      setError('Введите ИНН для проверки')
      return
    }
    setError(null)
    setFnsResult(null)
    if (!status) {
      setError('Сначала выберите тип лица')
      return
    }
    fnsMutation.mutate(
      {
        inn,
        legal_status: status,
        legal_name: legalName || undefined,
        kpp: kpp || undefined,
        ogrn: isLegalEntity ? ogrn || undefined : undefined,
        ogrnip: isIE ? ogrnip || undefined : undefined,
        passport_series: isIndividual ? passportSeries || undefined : undefined,
        passport_number: isIndividual ? passportNumber || undefined : undefined,
      },
      {
        onSuccess: (result) =>
          setFnsResult({ is_valid: result.is_valid, warnings: result.warnings, errors: result.errors }),
        onError: () => setError('Ошибка проверки через ФНС'),
      },
    )
  }

  const handleSave = () => {
    if (!status || !legalName || !inn) {
      setError('Заполните обязательные поля')
      return
    }
    if (isIndividual || isSelfEmployed) {
      if (!passportSeries || !passportNumber || !passportIssuedBy || !passportIssuedAt) {
        setError('Заполните паспортные данные — они необходимы для договора и ОРД')
        return
      }
      if (passportSeries.length !== 4 || passportNumber.length !== 6) {
        setError('Неверный формат паспорта: серия 4 цифры, номер 6 цифр')
        return
      }
    }
    setError(null)
    const data: Record<string, unknown> = { legal_status: status, legal_name: legalName, inn }
    if (fields.includes('kpp')) data.kpp = kpp
    if (fields.includes('ogrn')) data.ogrn = ogrn
    if (fields.includes('ogrnip')) data.ogrnip = ogrnip
    if (fields.includes('address')) data.address = address
    if (fields.includes('tax_regime') && taxRegime) data.tax_regime = taxRegime
    if (showBank && bankName) data.bank_name = bankName
    if (showBank && bankAccount) data.bank_account = bankAccount
    if (showBank && bankBik) data.bank_bik = bankBik
    if (showBank && bankCorrAccount) data.bank_corr_account = bankCorrAccount
    if (fields.includes('yoomoney_wallet')) data.yoomoney_wallet = yoomoneyWallet
    if (isIndividual || isSelfEmployed) {
      data.passport_series = passportSeries
      data.passport_number = passportNumber
      data.passport_issued_by = passportIssuedBy
      data.passport_issue_date = passportIssuedAt
    }

    if (existingProfile) {
      updateMutation.mutate(data, {
        onSuccess: () => navigate('/legal-profile/view'),
        onError: () => setError('Ошибка сохранения'),
      })
    } else {
      createMutation.mutate(data, {
        onSuccess: () => navigate('/legal-profile/view'),
        onError: () => setError('Ошибка сохранения'),
      })
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending
  const step = status ? (showBank ? 3 : 2) : 1

  const completeness = computeCompleteness({
    status,
    legalName,
    inn,
    address,
    bankAccount,
    bankBik,
    passportSeries,
    passportNumber,
  })

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Документы', 'Юридический профиль']}
        title="Юридический профиль"
        subtitle="Укажите реквизиты — мы используем их в договорах, чеках и актах"
        action={
          <Button variant="secondary" iconLeft="docs">
            Шаблон заполнения
          </Button>
        }
      />

      <div className="bg-harbor-card border border-border rounded-xl py-[18px] px-[22px] mb-4">
        <StepIndicator
          total={4}
          current={step}
          labels={['Тип лица', 'Реквизиты', 'Банк', 'Подписание']}
        />
      </div>

      {error && (
        <div className="mb-4">
          <Notification type="danger">{error}</Notification>
        </div>
      )}

      <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(0, 1.7fr) minmax(300px, 1fr)' }}>
        <div className="flex flex-col gap-4">
          <SectionCard title="Тип налогоплательщика" subtitle="Определяет, какие документы формирует платформа">
            <div className="grid gap-2.5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
              {LEGAL_TYPES.map((t) => {
                const on = status === t.id
                const tc = toneTileClass[t.tone]
                return (
                  <button
                    key={t.id}
                    onClick={() => setStatus(t.id)}
                    className={`py-3.5 px-3.5 rounded-[10px] border flex gap-[11px] items-start text-left transition-all ${
                      on
                        ? `${tc.border} ${tc.bg} ${tc.text} ring-[3px] ring-current/15`
                        : 'bg-harbor-elevated border-border text-text-primary hover:border-border-active'
                    }`}
                  >
                    <span
                      className={`w-[34px] h-[34px] rounded-lg grid place-items-center flex-shrink-0 ${tc.iconBg} ${tc.iconText}`}
                    >
                      <Icon name={t.icon} size={16} />
                    </span>
                    <div className="min-w-0">
                      <div className="font-display text-sm font-bold text-text-primary">{t.label}</div>
                      <div className="text-[11.5px] text-text-tertiary mt-0.5">{t.sub}</div>
                    </div>
                  </button>
                )
              })}
            </div>
          </SectionCard>

          {status && (
            <SectionCard title="Основные реквизиты" subtitle={LEGAL_TYPES.find((t) => t.id === status)?.label}>
              <div className="grid grid-cols-2 gap-3.5">
                <LPField
                  label={isLegalEntity ? 'Название организации' : isIE ? 'ФИО ИП' : 'ФИО'}
                  value={legalName}
                  onChange={setLegalName}
                  span={2}
                />
                <LPField
                  label="ИНН"
                  mono
                  value={inn}
                  onChange={setInn}
                  onBlur={(v) => {
                    if (v.length >= 10) innMutation.mutate(v)
                  }}
                  placeholder="10 или 12 цифр"
                  hint={innMutation.data && !innMutation.data.valid ? 'Неверный ИНН' : undefined}
                  hintTone={innMutation.data && !innMutation.data.valid ? 'danger' : 'neutral'}
                />
                {fields.includes('kpp') && <LPField label="КПП" mono value={kpp} onChange={setKpp} />}
                {fields.includes('ogrn') && <LPField label="ОГРН" mono value={ogrn} onChange={setOgrn} />}
                {fields.includes('ogrnip') && <LPField label="ОГРНИП" mono value={ogrnip} onChange={setOgrnip} />}
                {fields.includes('tax_regime') && (
                  <LPWrap span={2} label="Налоговый режим">
                    <Select value={taxRegime} onChange={setTaxRegime} options={TAX_REGIME_OPTIONS} placeholder="Выберите…" />
                  </LPWrap>
                )}
                {fields.includes('address') && (
                  <LPWrap span={2} label="Юридический адрес">
                    <Textarea value={address} onChange={setAddress} rows={2} />
                  </LPWrap>
                )}
                {fields.includes('yoomoney_wallet') && (
                  <LPField
                    span={2}
                    label="Кошелёк ЮMoney"
                    mono
                    value={yoomoneyWallet}
                    onChange={setYoomoneyWallet}
                    placeholder="41001XXXXXXXXXX"
                    hint="Выплаты будут приходить на ЮMoney-кошелёк"
                  />
                )}
              </div>
            </SectionCard>
          )}

          {showBank && (
            <SectionCard title="Банковские реквизиты" subtitle="На этот счёт поступают выплаты">
              <div className="grid grid-cols-2 gap-3.5">
                <LPField label="БИК" mono value={bankBik} onChange={setBankBik} placeholder="044525225" />
                <LPField label="Банк" value={bankName} onChange={setBankName} placeholder="ПАО СБЕРБАНК" hint="Подставится автоматически" />
                <LPField span={2} label="Расчётный счёт" mono value={bankAccount} onChange={setBankAccount} placeholder="40702810…" />
                <LPField
                  span={2}
                  label="Корреспондентский счёт"
                  mono
                  value={bankCorrAccount}
                  onChange={setBankCorrAccount}
                  placeholder="30101810…"
                />
              </div>
              <div className="mt-4 p-3 bg-accent-muted border border-accent/15 rounded-lg flex gap-2.5 items-start">
                <Icon name="lock" size={14} className="text-accent mt-0.5 flex-shrink-0" />
                <div className="text-xs text-text-secondary leading-[1.5]">
                  Реквизиты зашифрованы и хранятся согласно 152-ФЗ. Доступ только у вас и банка-получателя.
                </div>
              </div>
            </SectionCard>
          )}

          {(isIndividual || isSelfEmployed) && (
            <SectionCard title="Паспортные данные" subtitle="Необходимы для договора и ОРД">
              <div className="grid grid-cols-2 gap-3.5">
                <LPField
                  label="Серия"
                  mono
                  value={passportSeries}
                  onChange={(v) => setPassportSeries(v.replace(/\D/g, '').slice(0, 4))}
                  placeholder="4510"
                />
                <LPField
                  label="Номер"
                  mono
                  value={passportNumber}
                  onChange={(v) => setPassportNumber(v.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                />
                <LPWrap span={2} label="Кем выдан">
                  <Textarea value={passportIssuedBy} onChange={setPassportIssuedBy} placeholder="ОУФМС России по г. Москве" rows={2} />
                </LPWrap>
                <LPWrap span={2} label="Дата выдачи">
                  <input
                    type="date"
                    value={passportIssuedAt}
                    onChange={(e) => setPassportIssuedAt(e.target.value)}
                    className="w-full py-2.5 px-3 bg-harbor-elevated border border-border rounded-lg text-text-primary font-body text-[13px] outline-none focus:border-accent transition-colors"
                  />
                </LPWrap>
              </div>
            </SectionCard>
          )}

          {fnsResult && (
            <SectionCard title="Результат проверки ФНС">
              {fnsResult.is_valid ? (
                <Notification type="success">
                  ИНН прошёл проверку по контрольной сумме
                  {fnsResult.warnings.length > 0 && (
                    <div className="mt-2 space-y-0.5">
                      {fnsResult.warnings.map((w) => (
                        <p key={w} className="text-sm text-warning">
                          {w}
                        </p>
                      ))}
                    </div>
                  )}
                </Notification>
              ) : (
                <Notification type="danger">
                  Ошибки валидации:
                  <div className="mt-2 space-y-0.5">
                    {fnsResult.errors.map((e) => (
                      <p key={e.field} className="text-sm text-danger">
                        • {e.field}: {e.message}
                      </p>
                    ))}
                  </div>
                </Notification>
              )}
            </SectionCard>
          )}

          <div className="flex justify-between gap-2.5 flex-wrap">
            <Button variant="secondary" iconLeft="arrow-left" onClick={() => navigate('/cabinet')}>
              Назад
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={handleValidate} loading={fnsMutation.isPending} disabled={!inn}>
                Проверить ИНН
              </Button>
              <Button variant="primary" iconRight="arrow-right" loading={isSaving} onClick={handleSave}>
                {isSaving ? 'Сохранение…' : 'Сохранить и далее'}
              </Button>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3.5">
          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="flex items-center gap-3.5">
              <LPRing pct={completeness.pct} />
              <div>
                <div className="font-display text-sm font-semibold text-text-primary">Профиль заполнен</div>
                <div className="text-xs text-text-tertiary mt-0.5">
                  {completeness.filled} из {completeness.total} полей
                </div>
              </div>
            </div>
            <ul className="list-none p-0 m-0 mt-3.5 flex flex-col gap-1.5">
              {completeness.checks.map((s) => (
                <li key={s.label} className="flex items-center gap-2 text-[12.5px]">
                  <span
                    className={`w-4 h-4 rounded-full grid place-items-center flex-shrink-0 ${
                      s.done ? 'bg-success text-white' : 'bg-harbor-elevated text-text-tertiary'
                    }`}
                  >
                    {s.done ? (
                      <Icon name="check" size={10} strokeWidth={2.5} />
                    ) : (
                      <span className="w-1 h-1 rounded-full bg-text-tertiary" />
                    )}
                  </span>
                  <span className={s.done ? 'text-text-primary' : 'text-text-secondary'}>{s.label}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-[18px]">
            <div className="font-display text-[13px] font-semibold text-text-primary mb-2.5">
              Зачем это нужно
            </div>
            <ul className="list-none p-0 m-0 flex flex-col gap-2.5">
              {[
                { icon: 'docs' as IconName, text: 'Формируем договоры и акты автоматически' },
                { icon: 'ruble' as IconName, text: 'Чеки и закрывающие документы за вас' },
                { icon: 'lock' as IconName, text: 'Соответствие 54-ФЗ, 152-ФЗ, НК РФ' },
                { icon: 'zap' as IconName, text: 'Выплаты в тот же день после подписания' },
              ].map((r) => (
                <li key={r.text} className="flex gap-2.5 text-[12.5px] text-text-secondary leading-[1.5]">
                  <Icon name={r.icon} size={14} className="text-accent mt-0.5 flex-shrink-0" />
                  {r.text}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-harbor-elevated border border-dashed border-border rounded-xl p-3.5 flex items-center gap-2.5 text-xs text-text-secondary">
            <Icon name="info" size={13} className="text-text-tertiary" />
            Поля ИНН/ОГРН подтягиваются из ФНС при вводе
          </div>
        </div>
      </div>
    </div>
  )
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section className="bg-harbor-card border border-border rounded-xl p-5">
      <div className="mb-4">
        <div className="font-display text-[13.5px] font-semibold text-text-primary tracking-[-0.005em]">
          {title}
        </div>
        {subtitle && <div className="text-xs text-text-tertiary mt-[3px]">{subtitle}</div>}
      </div>
      {children}
    </section>
  )
}

function LPField({
  label,
  value,
  onChange,
  onBlur,
  placeholder,
  mono,
  span,
  hint,
  hintTone,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  onBlur?: (v: string) => void
  placeholder?: string
  mono?: boolean
  span?: 1 | 2
  hint?: string
  hintTone?: 'neutral' | 'danger'
}) {
  return (
    <div style={{ gridColumn: span === 2 ? '1 / -1' : 'auto' }}>
      <div className="text-[11px] font-bold tracking-[0.06em] uppercase text-text-tertiary mb-1.5">
        {label}
      </div>
      <input
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => onBlur?.(e.target.value)}
        placeholder={placeholder}
        className={`w-full py-2.5 px-3 bg-harbor-elevated border border-border rounded-lg text-text-primary text-[13px] outline-none focus:border-accent transition-colors ${
          mono ? 'font-mono tabular-nums' : 'font-body'
        }`}
      />
      {hint && (
        <div className={`text-[11px] mt-1.5 ${hintTone === 'danger' ? 'text-danger' : 'text-text-tertiary'}`}>
          {hint}
        </div>
      )}
    </div>
  )
}

function LPWrap({
  label,
  span,
  children,
}: {
  label: string
  span?: 1 | 2
  children: React.ReactNode
}) {
  return (
    <div style={{ gridColumn: span === 2 ? '1 / -1' : 'auto' }}>
      <div className="text-[11px] font-bold tracking-[0.06em] uppercase text-text-tertiary mb-1.5">
        {label}
      </div>
      {children}
    </div>
  )
}

function LPRing({ pct }: { pct: number }) {
  const r = 22
  const c = 2 * Math.PI * r
  return (
    <svg width="58" height="58" style={{ transform: 'rotate(-90deg)' }}>
      <circle cx="29" cy="29" r={r} stroke="var(--color-harbor-elevated)" strokeWidth="5" fill="none" />
      <circle
        cx="29"
        cy="29"
        r={r}
        stroke="var(--color-accent)"
        strokeWidth="5"
        fill="none"
        strokeDasharray={c}
        strokeDashoffset={c - (c * pct) / 100}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 400ms ease' }}
      />
      <text
        x="29"
        y="29"
        transform="rotate(90 29 29)"
        textAnchor="middle"
        dominantBaseline="central"
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 13,
          fontWeight: 700,
          fill: 'var(--color-text-primary)',
        }}
      >
        {pct}%
      </text>
    </svg>
  )
}

function computeCompleteness(s: {
  status: string
  legalName: string
  inn: string
  address: string
  bankAccount: string
  bankBik: string
  passportSeries: string
  passportNumber: string
}) {
  const checks = [
    { label: 'ИНН и наименование', done: !!s.inn && !!s.legalName },
    { label: 'Юридический адрес', done: !!s.address },
    { label: 'Банковский счёт', done: !!s.bankAccount && !!s.bankBik },
    { label: 'Паспорт (физлицо / самозанятый)', done: !!s.passportSeries && !!s.passportNumber },
  ]
  const filled = checks.filter((c) => c.done).length
  const total = checks.length
  return {
    checks,
    filled,
    total,
    pct: Math.round((filled / total) * 100),
  }
}
