import { useState, useEffect } from 'react'
import { Card, Button, Notification, Skeleton } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { usePlatformSettings, useUpdatePlatformSettings } from '@/hooks/useAdminQueries'
import type { PlatformSettings } from '@/lib/types/platform'

const FIELDS: { key: keyof PlatformSettings; label: string; placeholder: string }[] = [
  { key: 'legal_name', label: 'Юридическое наименование', placeholder: 'ООО «РекХарбор»' },
  { key: 'inn', label: 'ИНН', placeholder: '7700000000' },
  { key: 'kpp', label: 'КПП', placeholder: '770001001' },
  { key: 'ogrn', label: 'ОГРН', placeholder: '1027700000000' },
  { key: 'address', label: 'Юридический адрес', placeholder: 'г. Москва, ул. ...' },
  { key: 'bank_name', label: 'Банк', placeholder: 'АО «Тинькофф Банк»' },
  { key: 'bank_account', label: 'Расчётный счёт (р/с)', placeholder: '40702810000000000000' },
  { key: 'bank_bik', label: 'БИК', placeholder: '044525974' },
  { key: 'bank_corr_account', label: 'Корреспондентский счёт (к/с)', placeholder: '30101810145250000974' },
]

export default function AdminPlatformSettings() {
  const { data: user, isLoading: userLoading } = useMe()
  const { data: settings, isLoading: settingsLoading, isError } = usePlatformSettings(!!user?.is_admin)
  const saveMutation = useUpdatePlatformSettings()

  const [form, setForm] = useState<PlatformSettings>({
    legal_name: '', inn: '', kpp: '', ogrn: '', address: '',
    bank_name: '', bank_account: '', bank_bik: '', bank_corr_account: '',
  })
  const [success, setSuccess] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!settings) return
    setForm({
      legal_name: settings.legal_name ?? '',
      inn: settings.inn ?? '',
      kpp: settings.kpp ?? '',
      ogrn: settings.ogrn ?? '',
      address: settings.address ?? '',
      bank_name: settings.bank_name ?? '',
      bank_account: settings.bank_account ?? '',
      bank_bik: settings.bank_bik ?? '',
      bank_corr_account: settings.bank_corr_account ?? '',
    })
  }, [settings])
  /* eslint-enable react-hooks/set-state-in-effect */

  const error = saveError ?? (isError ? 'Не удалось загрузить реквизиты' : null)

  const handleSave = () => {
    setSaveError(null)
    setSuccess(false)
    saveMutation.mutate(form, {
      onSuccess: () => setSuccess(true),
      onError: () => setSaveError('Не удалось сохранить реквизиты'),
    })
  }

  if (userLoading || settingsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-48" />
      </div>
    )
  }

  if (!user?.is_admin) {
    return <Notification type="danger">Доступ запрещён</Notification>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Реквизиты платформы</h1>
      <p className="text-sm text-text-secondary">
        Заполните данные — они подставляются в договоры с владельцами каналов и рекламодателями.
      </p>

      {error && <Notification type="danger">{error}</Notification>}
      {success && <Notification type="success">Реквизиты сохранены</Notification>}

      <Card>
        <div className="space-y-3">
          {FIELDS.map(({ key, label, placeholder }) => (
            <div key={key}>
              <label className="block text-sm text-text-secondary mb-1">{label}</label>
              <input
                className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
                value={form[key] ?? ''}
                placeholder={placeholder}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
              />
            </div>
          ))}
        </div>
      </Card>

      <Button variant="primary" fullWidth loading={saveMutation.isPending} onClick={handleSave}>
        {saveMutation.isPending ? 'Сохранение...' : '💾 Сохранить'}
      </Button>
    </div>
  )
}
