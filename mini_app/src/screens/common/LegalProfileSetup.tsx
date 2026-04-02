import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button, Card, Notification, StepIndicator } from '@/components/ui'
import { LegalStatusSelector } from '@/components/LegalStatusSelector'
import { useLegalProfileStore } from '@/stores/legalProfileStore'
import {
  useRequiredFields,
  useCreateLegalProfile,
  useUpdateLegalProfile,
  useValidateInn,
  useMyLegalProfile,
} from '@/hooks/useLegalProfileQueries'
import type { TaxRegime } from '@/lib/types'

const TAX_REGIME_OPTIONS: { value: TaxRegime; label: string }[] = [
  { value: 'osno', label: 'ОСНО' },
  { value: 'usn', label: 'УСН' },
  { value: 'usn_d', label: 'УСН (доходы)' },
  { value: 'usn_dr', label: 'УСН (доходы − расходы)' },
  { value: 'patent', label: 'Патент (ПСН)' },
  { value: 'npd', label: 'НПД' },
  { value: 'ndfl', label: 'НДФЛ' },
]

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 'var(--rh-radius-sm, 8px)',
  border: '1px solid var(--rh-border, rgba(255,255,255,0.12))',
  background: 'var(--rh-surface, rgba(255,255,255,0.04))',
  color: 'inherit',
  fontSize: 'var(--rh-text-sm, 14px)',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 'var(--rh-text-xs, 12px)',
  color: 'var(--rh-text-muted)',
  marginBottom: 4,
}

export default function LegalProfileSetup() {
  const navigate = useNavigate()
  const store = useLegalProfileStore()
  const { data: existingProfile } = useMyLegalProfile()
  const { data: requiredFields } = useRequiredFields(store.selectedStatus ?? undefined)
  const createMutation = useCreateLegalProfile()
  const updateMutation = useUpdateLegalProfile()
  const innMutation = useValidateInn()

  const { currentStep, selectedStatus, formData, setStep, setSelectedStatus, updateFormData, reset } = store

  // --- Pre-fill from existing profile on mount (S7 addition) ---
  useEffect(() => {
    if (existingProfile && !selectedStatus) {
      setSelectedStatus(existingProfile.legal_status)
      updateFormData({
        legal_status: existingProfile.legal_status,
        inn: existingProfile.inn ?? undefined,
        kpp: existingProfile.kpp ?? undefined,
        ogrn: existingProfile.ogrn ?? undefined,
        ogrnip: existingProfile.ogrnip ?? undefined,
        legal_name: existingProfile.legal_name ?? undefined,
        address: existingProfile.address ?? undefined,
        tax_regime: existingProfile.tax_regime ?? undefined,
        bank_name: existingProfile.bank_name ?? undefined,
        bank_account: existingProfile.bank_account ?? undefined,
        bank_bik: existingProfile.bank_bik ?? undefined,
        bank_corr_account: existingProfile.bank_corr_account ?? undefined,
        yoomoney_wallet: existingProfile.yoomoney_wallet ?? undefined,
      })
      setStep(1)
    }
  }, [existingProfile]) // eslint-disable-line react-hooks/exhaustive-deps
  // --- end pre-fill ---

  const handleNext = () => setStep(currentStep + 1)
  const handleBack = () => setStep(currentStep - 1)

  const handleSave = () => {
    const data = formData as Parameters<typeof createMutation.mutate>[0]
    if (existingProfile) {
      updateMutation.mutate(data, {
        onSuccess: () => {
          reset()
          navigate('/legal-profile/view')
        },
      })
    } else {
      createMutation.mutate(data, {
        onSuccess: () => {
          reset()
          navigate('/legal-profile/view')
        },
      })
    }
  }

  const isSaving = createMutation.isPending || updateMutation.isPending
  const saveError = createMutation.error || updateMutation.error

  return (
    <ScreenShell>
      <StepIndicator total={4} current={currentStep} labels={['Статус', 'Данные', 'Реквизиты', 'Подтверждение']} />

      {currentStep === 0 && (
        <>
          <p style={{ fontWeight: 600, marginBottom: 12 }}>Выберите юридический статус</p>
          <LegalStatusSelector value={selectedStatus} onChange={setSelectedStatus} />
          <div style={{ marginTop: 16 }}>
            <Button
              variant="primary"
              fullWidth
              disabled={!selectedStatus}
              onClick={handleNext}
            >
              Далее →
            </Button>
          </div>
        </>
      )}

      {currentStep === 1 && (
        <>
          <p style={{ fontWeight: 600, marginBottom: 12 }}>Основные данные</p>
          <Card>
            <label style={labelStyle}>Название / ФИО *</label>
            <input
              style={inputStyle}
              value={formData.legal_name ?? ''}
              onChange={(e) => updateFormData({ legal_name: e.target.value })}
              placeholder="ООО Ромашка / Иванов Иван Иванович"
            />

            <label style={{ ...labelStyle, marginTop: 12 }}>ИНН *</label>
            <input
              style={inputStyle}
              value={formData.inn ?? ''}
              onChange={(e) => updateFormData({ inn: e.target.value })}
              onBlur={(e) => {
                if (e.target.value.length >= 10) innMutation.mutate(e.target.value)
              }}
              placeholder="ИНН"
            />
            {innMutation.data && !innMutation.data.valid && (
              <p style={{ margin: '4px 0 0', color: 'var(--rh-danger)', fontSize: 'var(--rh-text-xs, 12px)' }}>
                Неверный ИНН
              </p>
            )}

            {requiredFields?.fields.includes('kpp') && (
              <>
                <label style={{ ...labelStyle, marginTop: 12 }}>КПП</label>
                <input
                  style={inputStyle}
                  value={formData.kpp ?? ''}
                  onChange={(e) => updateFormData({ kpp: e.target.value })}
                  placeholder="КПП"
                />
              </>
            )}

            {requiredFields?.fields.includes('ogrn') && (
              <>
                <label style={{ ...labelStyle, marginTop: 12 }}>ОГРН</label>
                <input
                  style={inputStyle}
                  value={formData.ogrn ?? ''}
                  onChange={(e) => updateFormData({ ogrn: e.target.value })}
                  placeholder="ОГРН"
                />
              </>
            )}

            {requiredFields?.fields.includes('ogrnip') && (
              <>
                <label style={{ ...labelStyle, marginTop: 12 }}>ОГРНИП</label>
                <input
                  style={inputStyle}
                  value={formData.ogrnip ?? ''}
                  onChange={(e) => updateFormData({ ogrnip: e.target.value })}
                  placeholder="ОГРНИП"
                />
              </>
            )}

            {requiredFields?.tax_regime_required && (
              <>
                <label style={{ ...labelStyle, marginTop: 12 }}>Система налогообложения</label>
                <select
                  style={inputStyle}
                  value={formData.tax_regime ?? ''}
                  onChange={(e) => updateFormData({ tax_regime: e.target.value as TaxRegime })}
                >
                  <option value="">Выберите...</option>
                  {TAX_REGIME_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </>
            )}
          </Card>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <Button variant="secondary" onClick={handleBack}>← Назад</Button>
            <Button
              variant="primary"
              fullWidth
              disabled={!formData.legal_name || !formData.inn}
              onClick={handleNext}
            >
              Далее →
            </Button>
          </div>
        </>
      )}

      {currentStep === 2 && (
        <>
          <p style={{ fontWeight: 600, marginBottom: 12 }}>Платёжные реквизиты</p>
          <Card>
            {requiredFields?.show_bank_details && (
              <>
                <label style={labelStyle}>Название банка</label>
                <input style={inputStyle} value={formData.bank_name ?? ''} onChange={(e) => updateFormData({ bank_name: e.target.value })} placeholder="Сбербанк" />
                <label style={{ ...labelStyle, marginTop: 12 }}>Расчётный счёт</label>
                <input style={inputStyle} value={formData.bank_account ?? ''} onChange={(e) => updateFormData({ bank_account: e.target.value })} placeholder="40702810..." />
                <label style={{ ...labelStyle, marginTop: 12 }}>БИК</label>
                <input style={inputStyle} value={formData.bank_bik ?? ''} onChange={(e) => updateFormData({ bank_bik: e.target.value })} placeholder="044525225" />
                <label style={{ ...labelStyle, marginTop: 12 }}>Корр. счёт</label>
                <input style={inputStyle} value={formData.bank_corr_account ?? ''} onChange={(e) => updateFormData({ bank_corr_account: e.target.value })} placeholder="30101810..." />
              </>
            )}
            {requiredFields?.show_yoomoney && (
              <>
                <label style={{ ...labelStyle, marginTop: requiredFields.show_bank_details ? 12 : 0 }}>ЮMoney кошелёк</label>
                <input style={inputStyle} value={formData.yoomoney_wallet ?? ''} onChange={(e) => updateFormData({ yoomoney_wallet: e.target.value })} placeholder="41001..." />
              </>
            )}
            {requiredFields?.show_passport && (
              <>
                <label style={{ ...labelStyle, marginTop: 12 }}>Серия паспорта</label>
                <input style={inputStyle} value={formData.passport_series ?? ''} onChange={(e) => updateFormData({ passport_series: e.target.value })} placeholder="1234" />
                <label style={{ ...labelStyle, marginTop: 12 }}>Номер паспорта</label>
                <input style={inputStyle} value={formData.passport_number ?? ''} onChange={(e) => updateFormData({ passport_number: e.target.value })} placeholder="567890" />
                <label style={{ ...labelStyle, marginTop: 12 }}>Кем выдан</label>
                <input style={inputStyle} value={formData.passport_issued_by ?? ''} onChange={(e) => updateFormData({ passport_issued_by: e.target.value })} placeholder="УФМС России..." />
              </>
            )}
          </Card>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <Button variant="secondary" onClick={handleBack}>← Назад</Button>
            <Button variant="primary" fullWidth onClick={handleNext}>Далее →</Button>
          </div>
        </>
      )}

      {currentStep === 3 && (
        <>
          <p style={{ fontWeight: 600, marginBottom: 12 }}>Подтверждение</p>
          <Card title="Введённые данные">
            {Object.entries(formData).map(([key, val]) => (
              val ? (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 'var(--rh-text-sm, 14px)' }}>
                  <span style={{ color: 'var(--rh-text-muted)' }}>{key}</span>
                  <span>{String(val)}</span>
                </div>
              ) : null
            ))}
          </Card>

          {saveError && (
            <Notification type="danger">Ошибка сохранения. Попробуйте ещё раз.</Notification>
          )}

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <Button variant="secondary" onClick={handleBack}>← Назад</Button>
            <Button variant="primary" fullWidth disabled={isSaving} onClick={handleSave}>
              {isSaving ? '⏳ Сохранение...' : '✅ Сохранить'}
            </Button>
          </div>
        </>
      )}
    </ScreenShell>
  )
}
