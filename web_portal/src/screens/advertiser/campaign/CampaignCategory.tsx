import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { StepIndicator, CategoryGrid, Toggle, Skeleton } from '@shared/ui'
import { CATEGORIES, PLAN_INFO } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { useCategories } from '@/hooks/useCategoryQueries'

export default function CampaignCategory() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const { data: user } = useMe()
  const { data: apiCategories, isLoading: catsLoading } = useCategories()

  const ALL_KEY = '__all__'
  // Use API categories if available, fall back to static CATEGORIES constant
  const rawCats = apiCategories ?? CATEGORIES.map((c) => ({ key: c.key, name: c.name, emoji: c.emoji }))
  const baseCats = rawCats.map((c) => ({ id: c.key, label: c.name, icon: c.emoji }))
  const cats = [{ id: ALL_KEY, label: 'Все каналы', icon: '📋' }, ...baseCats]

  useEffect(() => {
    store.reset()
    // Set allowed formats based on user plan
    const plan = user?.plan ?? 'free'
    const formats = PLAN_INFO[plan]?.formats ?? ['post_24h']
    store.setPlanAllowedFormats(formats)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  if (catsLoading) {
    return (
      <div className="space-y-6">
        <StepIndicator total={6} current={1} labels={['', 'Шаг 1 — Выберите тематику']} />
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-20" />)}
        </div>
      </div>
    )
  }

  const handleSelect = (key: string) => {
    store.setCategory(key === ALL_KEY ? null : key)
    store.nextStep()
    navigate('/adv/campaigns/new/channels')
  }

  return (
    <div className="space-y-6">
      <StepIndicator total={6} current={1} labels={['', 'Шаг 1 — Выберите тематику']} />

      <p className="text-text-secondary">Выберите категорию для вашей рекламы</p>

      {user?.is_admin && (
        <Toggle
          label="🧪 Тестовый режим кампании"
          checked={store.isTest}
          onChange={store.setIsTest}
        />
      )}

      <CategoryGrid
        categories={cats}
        selected={
          store.category
            ? [store.category]
            : store.step > 1
            ? [ALL_KEY]
            : []
        }
        onToggle={handleSelect}
      />
    </div>
  )
}
