import { useState, useEffect } from 'react'
import { Card, Button, Notification, Skeleton } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { api } from '@shared/api/client'

interface PlatformSettings {
  legal_name: string | null
  inn: string | null
  kpp: string | null
  ogrn: string | null
  address: string | null
  bank_name: string | null
  bank_account: string | null
  bank_bik: string | null
  bank_corr_account: string | null
}

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

  const [form, setForm] = useState<PlatformSettings>({
    legal_name: '', inn: '', kpp: '', ogrn: '', address: '',
    bank_name: '', bank_account: '', bank_bik: '', bank_corr_account: '',
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!user?.is_admin) return
    setLoading(true)
    api.get('admin/platform-settings')
      .json<PlatformSettings>()
      .then((data) => setForm({
        legal_name: data.legal_name ?? '',
        inn: data.inn ?? '',
        kpp: data.kpp ?? '',
        ogrn: data.ogrn ?? '',
        address: data.address ?? '',
        bank_name: data.bank_name ?? '',
        bank_account: data.bank_account ?? '',
        bank_bik: data.bank_bik ?? '',
        bank_corr_account: data.bank_corr_account ?? '',
      }))
      .catch(() => setError('Не удалось загрузить реквизиты'))
      .finally(() => setLoading(false))
  }, [user?.is_admin])
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleSave = () => {
    setSaving(true)
    setError(null)
    setSuccess(false)
    api.put('admin/platform-settings', { json: form })
      .json()
      .then(() => setSuccess(true))
      .catch(() => setError('Не удалось сохранить реквизиты'))
      .finally(() => setSaving(false))
  }

  if (userLoading || loading) {
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

      <Button variant="primary" fullWidth loading={saving} onClick={handleSave}>
        {saving ? 'Сохранение...' : '💾 Сохранить'}
      </Button>
    </div>
  )
}
