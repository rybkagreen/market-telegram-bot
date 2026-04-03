/**
 * AdminPlatformSettings — редактирование реквизитов платформы
 * Данные подставляются в шаблоны договоров (HTML/PDF).
 */

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Card, Notification, Text } from '@/components/ui'
import { Button } from '@/components/ui'
import AdminNav from '@/components/admin/AdminNav'
import { useMe } from '@/hooks/queries'
import { api } from '@/api/client'
import styles from './AdminPlatformSettings.module.css'

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

const EMPTY: PlatformSettings = {
  legal_name: '', inn: '', kpp: '', ogrn: '', address: '',
  bank_name: '', bank_account: '', bank_bik: '', bank_corr_account: '',
}

const FIELDS: { key: keyof PlatformSettings; label: string; placeholder?: string }[] = [
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
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading } = useMe()
  const [form, setForm] = useState<PlatformSettings>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user?.is_admin) return
    api.get('admin/platform-settings').json<PlatformSettings>()
      .then((data) => {
        setForm({
          legal_name: data.legal_name ?? '',
          inn: data.inn ?? '',
          kpp: data.kpp ?? '',
          ogrn: data.ogrn ?? '',
          address: data.address ?? '',
          bank_name: data.bank_name ?? '',
          bank_account: data.bank_account ?? '',
          bank_bik: data.bank_bik ?? '',
          bank_corr_account: data.bank_corr_account ?? '',
        })
      })
      .catch(() => setError('Не удалось загрузить реквизиты'))
      .finally(() => setLoading(false))
  }, [user])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      await api.put('admin/platform-settings', { json: form })
      setSuccess(true)
    } catch {
      setError('Не удалось сохранить реквизиты')
    } finally {
      setSaving(false)
    }
  }

  if (userLoading) return null

  if (!user?.is_admin) {
    return (
      <ScreenShell>
        <Notification type="danger">Доступ запрещён.</Notification>
        <Button variant="secondary" fullWidth onClick={() => navigate('/')}>В главное меню</Button>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        <h1 className={styles.title}>Реквизиты платформы</h1>
        <Text variant="sm" color="muted" className={styles.subtitle}>
          Заполните данные — они подставляются в договора с владельцами каналов и рекламодателями.
        </Text>

        {error && <div className={styles.notificationWrap}><Notification type="danger">{error}</Notification></div>}
        {success && <div className={styles.notificationWrap}><Notification type="success">Реквизиты сохранены</Notification></div>}

        <Card>
          {loading ? (
            <Text variant="sm" color="muted" className={styles.loadingText}>Загрузка...</Text>
          ) : (
            <div className={styles.formContainer}>
              {FIELDS.map(({ key, label, placeholder }) => (
                <div key={key}>
                  <label className={styles.formLabel}>
                    {label}
                  </label>
                  <input
                    value={form[key] ?? ''}
                    placeholder={placeholder}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    className={styles.formInput}
                  />
                </div>
              ))}
              <Button variant="primary" fullWidth onClick={() => void handleSave()} disabled={saving}>
                {saving ? 'Сохранение...' : 'Сохранить'}
              </Button>
            </div>
          )}
        </Card>
      </main>
    </ScreenShell>
  )
}
