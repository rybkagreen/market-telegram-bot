import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, CategoryGrid, Toggle, Skeleton, Notification } from '@shared/ui'
import { CATEGORIES, PLAN_INFO } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { useCategories } from '@/hooks/useCategoryQueries'
import { CampaignWizardShell } from './_shell'

const ALL_KEY = '__all__'

export default function CampaignCategory() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const { data: user } = useMe()
  const { data: apiCategories, isLoading: catsLoading } = useCategories()

  const rawCats = apiCategories ?? CATEGORIES.map((c) => ({ key: c.key, name: c.name, emoji: c.emoji }))
  const baseCats = rawCats.map((c) => ({ id: c.key, label: c.name, icon: c.emoji }))
  const cats = [{ id: ALL_KEY, label: 'Все каналы', icon: '📋' }, ...baseCats]

  useEffect(() => {
    store.reset()
    const plan = user?.plan ?? 'free'
    const formats = PLAN_INFO[plan]?.formats ?? ['post_24h']
    store.setPlanAllowedFormats(formats)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (key: string) => {
    store.setCategory(key === ALL_KEY ? null : key)
    store.nextStep()
    navigate('/adv/campaigns/new/channels')
  }

  return (
    <CampaignWizardShell
      step={1}
      title="Выберите тематику"
      subtitle="Подберите категорию, чтобы ограничить список каналов. «Все каналы» откроет полный каталог."
    >
      {user?.is_admin && (
        <Notification type="info">
          <Toggle
            label="Тестовый режим кампании — заявка не будет видна владельцам"
            checked={store.isTest}
            onChange={store.setIsTest}
          />
        </Notification>
      )}

      {catsLoading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-24" />
          ))}
        </div>
      ) : (
        <CategoryGrid
          categories={cats}
          selected={store.category ? [store.category] : store.step > 1 ? [ALL_KEY] : []}
          onToggle={handleSelect}
        />
      )}

      <p className="text-[12.5px] text-text-tertiary">
        Шаг 1 из 6 · После выбора тематики вы перейдёте к выбору каналов.
      </p>

      <div className="h-4" />

      <div className="flex justify-end">
        <Button
          variant="ghost"
          iconRight="arrow-right"
          disabled={!store.category && store.step <= 1}
          onClick={() => {
            store.nextStep()
            navigate('/adv/campaigns/new/channels')
          }}
        >
          Пропустить — все каналы
        </Button>
      </div>
    </CampaignWizardShell>
  )
}
