import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, CategoryGrid, Skeleton } from '@/components/ui'
import { CATEGORIES } from '@/lib/constants'
import { useCategories } from '@/hooks/queries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import styles from './CampaignCategory.module.css'

export default function CampaignCategory() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const { data: apiCategories, isLoading } = useCategories()

  const cats = (apiCategories ?? CATEGORIES).map((c) => ({ id: c.key, label: c.name, icon: c.emoji }))

  useEffect(() => {
    store.reset()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <ScreenShell>
      <StepIndicator
        total={6}
        current={0}
        labels={['Шаг 1 — Выберите тематику']}
      />

      <p className={styles.hint}>Выберите категорию для вашей рекламы</p>

      {isLoading ? (
        <Skeleton height={200} radius="md" />
      ) : (
        <CategoryGrid
          categories={cats}
          selected={store.category ? [store.category] : []}
          onToggle={(key) => {
            store.setCategory(key)
            store.nextStep()
            navigate('/adv/campaigns/new/channels')
          }}
        />
      )}
    </ScreenShell>
  )
}
