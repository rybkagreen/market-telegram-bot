import { useState, useEffect } from 'react'
import {
  Button,
  Notification,
  Skeleton,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { usePlatformSettings, useUpdatePlatformSettings } from '@/hooks/useAdminQueries'
import type { PlatformSettings } from '@/lib/types/platform'

type Group = 'entity' | 'bank'

const FIELDS: { key: keyof PlatformSettings; label: string; placeholder: string; group: Group }[] = [
  { key: 'legal_name', label: 'Юридическое наименование', placeholder: 'ООО «РекХарбор»', group: 'entity' },
  { key: 'inn', label: 'ИНН', placeholder: '7700000000', group: 'entity' },
  { key: 'kpp', label: 'КПП', placeholder: '770001001', group: 'entity' },
  { key: 'ogrn', label: 'ОГРН', placeholder: '1027700000000', group: 'entity' },
  { key: 'address', label: 'Юридический адрес', placeholder: 'г. Москва, ул. …', group: 'entity' },
  { key: 'bank_name', label: 'Банк', placeholder: 'АО «Тинькофф Банк»', group: 'bank' },
  { key: 'bank_account', label: 'Расчётный счёт (р/с)', placeholder: '40702810000000000000', group: 'bank' },
  { key: 'bank_bik', label: 'БИК', placeholder: '044525974', group: 'bank' },
  {
    key: 'bank_corr_account',
    label: 'Корреспондентский счёт (к/с)',
    placeholder: '30101810145250000974',
    group: 'bank',
  },
]

export default function AdminPlatformSettings() {
  const { data: user, isLoading: userLoading } = useMe()
  const { data: settings, isLoading: settingsLoading, isError } = usePlatformSettings(!!user?.is_admin)
  const saveMutation = useUpdatePlatformSettings()

  const [form, setForm] = useState<PlatformSettings>({
    legal_name: '',
    inn: '',
    kpp: '',
    ogrn: '',
    address: '',
    bank_name: '',
    bank_account: '',
    bank_bik: '',
    bank_corr_account: '',
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
      <div className="max-w-[1080px] mx-auto space-y-4">
        <Skeleton className="h-20" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!user?.is_admin) {
    return (
      <div className="max-w-[1080px] mx-auto">
        <Notification type="danger">Доступ запрещён</Notification>
      </div>
    )
  }

  const entityFields = FIELDS.filter((f) => f.group === 'entity')
  const bankFields = FIELDS.filter((f) => f.group === 'bank')

  return (
    <div className="max-w-[1080px] mx-auto">
      <ScreenHeader
        title="Реквизиты платформы"
        subtitle="Подставляются в договоры с владельцами каналов и рекламодателями."
      />

      {error && (
        <div className="mb-4">
          <Notification type="danger">{error}</Notification>
        </div>
      )}
      {success && (
        <div className="mb-4">
          <Notification type="success">Реквизиты сохранены.</Notification>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard icon="contract" title="Юридические данные">
          <div className="space-y-3">
            {entityFields.map((f) => (
              <FormRow key={String(f.key)}>
                <FormLabel>{f.label}</FormLabel>
                <input
                  className="w-full px-3 py-2 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 text-sm"
                  value={form[f.key] ?? ''}
                  placeholder={f.placeholder}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, [f.key]: e.target.value }))
                  }
                />
              </FormRow>
            ))}
          </div>
        </SectionCard>

        <SectionCard icon="bank" title="Платёжные реквизиты">
          <div className="space-y-3">
            {bankFields.map((f) => (
              <FormRow key={String(f.key)}>
                <FormLabel>{f.label}</FormLabel>
                <input
                  className="w-full px-3 py-2 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 text-sm font-mono tabular-nums"
                  value={form[f.key] ?? ''}
                  placeholder={f.placeholder}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, [f.key]: e.target.value }))
                  }
                />
              </FormRow>
            ))}
          </div>
        </SectionCard>
      </div>

      <div className="mt-5">
        <Button
          variant="primary"
          iconLeft="check"
          fullWidth
          loading={saveMutation.isPending}
          onClick={handleSave}
        >
          Сохранить реквизиты
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
      <div className="p-5">{children}</div>
    </div>
  )
}

function FormRow({ children }: { children: React.ReactNode }) {
  return <label className="block">{children}</label>
}

function FormLabel({ children }: { children: React.ReactNode }) {
  return (
    <span className="block text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
      {children}
    </span>
  )
}
