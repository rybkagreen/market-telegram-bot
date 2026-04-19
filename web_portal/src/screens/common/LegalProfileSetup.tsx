import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Notification, Select, Textarea } from '@shared/ui'
import {
  useMyLegalProfile,
  useCreateLegalProfile,
  useUpdateLegalProfile,
  useValidateInn,
  useRequiredFields,
  useValidateEntity,
} from '@/hooks/useLegalProfileQueries'

const LEGAL_STATUS_OPTIONS = [
  { value: 'individual', label: 'Физическое лицо' },
  { value: 'self_employed', label: 'Самозанятый (НПД)' },
  { value: 'individual_entrepreneur', label: 'ИП' },
  { value: 'legal_entity', label: 'Юридическое лицо (ООО)' },
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

export default function LegalProfileSetup() {
  const navigate = useNavigate()
  const { data: existingProfile } = useMyLegalProfile()
  const [status, setStatus] = useState('')
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
  const [fnsResult, setFnsResult] = useState<{ is_valid: boolean; warnings: string[]; errors: { field: string; message: string }[] } | null>(null)

  const fields = requiredFields?.fields ?? []
  const isLegalEntity = status === 'legal_entity'
  const isIE = status === 'individual_entrepreneur'
  const isSelfEmployed = status === 'self_employed'
  const showBank = isLegalEntity || isIE

  function getLegalNameLabel(): string {
    if (isLegalEntity) return 'Название организации *'
    if (isIE) return 'ФИО ИП *'
    return 'ФИО *'
  }

  // Pre-fill from existing profile
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (existingProfile) {
      setStatus(existingProfile.legal_status)
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
      // Passport data is not returned by backend (PII). Form starts blank
      // for existing profiles — the has_passport_data flag indicates whether
      // passport is already on file.
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

    fnsMutation.mutate(
      {
        inn,
        legal_status: status,
        legal_name: legalName || undefined,
        kpp: kpp || undefined,
        ogrn: isLegalEntity ? (ogrn || undefined) : undefined,
        ogrnip: isIE ? (ogrnip || undefined) : undefined,
        passport_series: status === 'individual' ? passportSeries || undefined : undefined,
        passport_number: status === 'individual' ? passportNumber || undefined : undefined,
      },
      {
        onSuccess: (result) => {
          setFnsResult({ is_valid: result.is_valid, warnings: result.warnings, errors: result.errors })
        },
        onError: () => setError('Ошибка проверки через ФНС'),
      },
    )
  }

  const handleSave = () => {
    if (!status || !legalName || !inn) {
      setError('Заполните обязательные поля')
      return
    }

    // Passport required for individuals and self-employed
    if (status === 'individual' || isSelfEmployed) {
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

    const data: Record<string, unknown> = {
      legal_status: status,
      legal_name: legalName,
      inn,
    }
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
    // Passport fields
    if (status === 'individual' || isSelfEmployed) {
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

  // ─── Step titles ───
  const statusLabel = LEGAL_STATUS_OPTIONS.find((o) => o.value === status)?.label ?? ''

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Юридический профиль</h1>

      {error && <Notification type="danger">{error}</Notification>}

      {/* Status */}
      <Card title="Юридический статус">
        <Select
          value={status}
          onChange={setStatus}
          options={LEGAL_STATUS_OPTIONS}
          placeholder="Выберите статус..."
        />
        {status && (
          <p className="text-sm text-text-secondary mt-2">
            Выбрано: <span className="font-medium text-text-primary">{statusLabel}</span>
          </p>
        )}
      </Card>

      {/* Basic info — shown only after status selected */}
      {status && (
        <Card title="Основные данные">
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-text-secondary mb-1">
                {getLegalNameLabel()}
              </label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                placeholder={isLegalEntity ? 'ООО «Ромашка»' : 'Иванов Иван Иванович'}
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">ИНН *</label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={inn}
                onChange={(e) => setInn(e.target.value)}
                onBlur={(e) => { if (e.target.value.length >= 10) innMutation.mutate(e.target.value) }}
                placeholder="ИНН"
              />
              {innMutation.data && !innMutation.data.valid && (
                <p className="text-xs text-danger mt-1">Неверный ИНН</p>
              )}
            </div>

            {fields.includes('kpp') && (
              <div>
                <label className="block text-sm text-text-secondary mb-1">КПП</label>
                <input
                  className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                  value={kpp}
                  onChange={(e) => setKpp(e.target.value)}
                  placeholder="КПП"
                />
              </div>
            )}
            {fields.includes('ogrn') && (
              <div>
                <label className="block text-sm text-text-secondary mb-1">ОГРН</label>
                <input
                  className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                  value={ogrn}
                  onChange={(e) => setOgrn(e.target.value)}
                  placeholder="ОГРН"
                />
              </div>
            )}
            {fields.includes('ogrnip') && (
              <div>
                <label className="block text-sm text-text-secondary mb-1">ОГРНИП</label>
                <input
                  className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                  value={ogrnip}
                  onChange={(e) => setOgrnip(e.target.value)}
                  placeholder="ОГРНИП"
                />
              </div>
            )}
            {fields.includes('tax_regime') && (
              <div>
                <label className="block text-sm text-text-secondary mb-1">Налоговый режим</label>
                <Select value={taxRegime} onChange={setTaxRegime} options={TAX_REGIME_OPTIONS} placeholder="Выберите..." />
              </div>
            )}
            {fields.includes('yoomoney_wallet') && (
              <div>
                <label className="block text-sm text-text-secondary mb-1">Кошелёк ЮMoney</label>
                <input
                  className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                  value={yoomoneyWallet}
                  onChange={(e) => setYoomoneyWallet(e.target.value)}
                  placeholder="41001XXXXXXXXXX"
                />
                <p className="text-xs text-text-tertiary mt-1">Выплаты будут приходить на ЮMoney-кошелёк</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Bank details — only for ООО and ИП */}
      {showBank && (
        <Card title="Банковские реквизиты">
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-text-secondary mb-1">Название банка</label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
                placeholder="Сбербанк"
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">Расчётный счёт</label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={bankAccount}
                onChange={(e) => setBankAccount(e.target.value)}
                placeholder="40702810..."
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">БИК</label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={bankBik}
                onChange={(e) => setBankBik(e.target.value)}
                placeholder="044525225"
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">Корр. счёт</label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={bankCorrAccount}
                onChange={(e) => setBankCorrAccount(e.target.value)}
                placeholder="30101810..."
              />
            </div>
          </div>
        </Card>
      )}

      {/* Passport — for individuals and self-employed */}
      {(isSelfEmployed || status === 'individual') && (
        <Card title="Паспортные данные">
          <p className="text-xs text-text-tertiary mb-3">
            Необходимы для заключения договора и передачи данных в ОРД
          </p>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm text-text-secondary mb-1">Серия *</label>
                <input
                  className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm font-mono"
                  value={passportSeries}
                  onChange={(e) => setPassportSeries(e.target.value.replace(/\D/g, '').slice(0, 4))}
                  placeholder="4510"
                  maxLength={4}
                />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Номер *</label>
                <input
                  className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm font-mono"
                  value={passportNumber}
                  onChange={(e) => setPassportNumber(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                  maxLength={6}
                />
              </div>
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">Кем выдан *</label>
              <Textarea
                value={passportIssuedBy}
                onChange={setPassportIssuedBy}
                placeholder="ОУФМС России по г. Москве"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm text-text-secondary mb-1">Дата выдачи *</label>
              <input
                type="date"
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={passportIssuedAt}
                onChange={(e) => setPassportIssuedAt(e.target.value)}
              />
            </div>
          </div>
        </Card>
      )}

      {/* Address — for all */}
      {status && fields.includes('address') && (
        <Card title="Адрес">
          <Textarea value={address} onChange={setAddress} placeholder="Юридический адрес" rows={2} />
        </Card>
      )}

      {/* FNS validation result */}
      {fnsResult && (
        <Card title="🏛️ Результат проверки ФНС">
          {fnsResult.is_valid ? (
            <Notification type="success">
              ✅ ИНН прошёл проверку по контрольной сумме
              {fnsResult.warnings.length > 0 && (
                <div className="mt-2">
                  {fnsResult.warnings.map((w, i) => (
                    <p key={i} className="text-sm text-warning">⚠️ {w}</p>
                  ))}
                </div>
              )}
            </Notification>
          ) : (
            <Notification type="danger">
              ❌ Ошибки валидации:
              {fnsResult.errors.map((e, i) => (
                <p key={i} className="text-sm text-danger mt-1">• {e.field}: {e.message}</p>
              ))}
            </Notification>
          )}
        </Card>
      )}

      {/* Actions */}
      <div className="space-y-3">
        <Button variant="ghost" fullWidth onClick={handleValidate} loading={fnsMutation.isPending} disabled={!inn}>
          🏛️ Проверить ИНН через ФНС
        </Button>
        <Button variant="primary" fullWidth loading={isSaving} onClick={handleSave}>
          {isSaving ? '⏳ Сохранение...' : '✅ Сохранить'}
        </Button>
        <Button variant="secondary" fullWidth onClick={() => navigate('/cabinet')}>
          ← Назад в кабинет
        </Button>
      </div>
    </div>
  )
}
