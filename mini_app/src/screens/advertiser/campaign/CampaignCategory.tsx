import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, CategoryGrid, Skeleton, Toggle } from '@/components/ui'
import { CATEGORIES } from '@/lib/constants'
import { useCategories } from '@/hooks/queries'
import { useMe } from '@/hooks/queries/useUserQueries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import styles from './CampaignCategory.module.css'

export default function CampaignCategory() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const { data: apiCategories, isLoading } = useCategories()
  const { data: user } = useMe()

  const ALL_KEY = '__all__'
  const baseCats = (apiCategories && apiCategories.length > 0 ? apiCategories : CATEGORIES).map(
    (c) => ({ id: c.key, label: c.name, icon: c.emoji }),
  )
  const cats = [{ id: ALL_KEY, label: 'Все каналы', icon: '📋' }, ...baseCats]

  useEffect(() => {
    store.reset()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelect = (key: string) => {
    store.setCategory(key === ALL_KEY ? null : key)
    store.nextStep()
    navigate('/adv/campaigns/new/channels')
  }

  return (
    <ScreenShell>
      <StepIndicator
        total={6}
        current={0}
        labels={['Шаг 1 — Выберите тематику']}
      />

      <p className={styles.hint}>Выберите категорию для вашей рекламы</p>

      {user?.is_admin && (
        <Toggle
          label="🧪 Тестовый режим кампании"
          checked={store.isTest}
          onChange={store.setIsTest}
        />
      )}

      {isLoading ? (
        <Skeleton height={200} radius="md" />
      ) : (
        <CategoryGrid
          categories={cats}
          selected={store.category ? [store.category] : store.category === null && store.step > 1 ? [ALL_KEY] : []}
          onToggle={handleSelect}
        />
      )}
    </ScreenShell>
  )
}
