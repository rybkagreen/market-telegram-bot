import { useNavigate } from 'react-router-dom'
import { Card, Notification, Button, Skeleton } from '@shared/ui'
import { PLAN_INFO, formatCurrency } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { usePlans, usePurchasePlan } from '@/hooks/useBillingQueries'
import type { Plan } from '@/lib/types'

interface PlanConfig {
  key: Plan
  features: string[]
  featured?: boolean
}

const PLANS: PlanConfig[] = [
  {
    key: 'free',
    features: ['1 активная кампания', 'Только пост 24ч', 'Базовая аналитика'],
  },
  {
    key: 'starter',
    features: [
      '5 активных кампаний',
      'Пост 24ч и 48ч',
      'AI-генерация текста × 3',
      'Расширенная аналитика',
    ],
  },
  {
    key: 'pro',
    featured: true,
    features: [
      '20 активных кампаний',
      'Пост 24ч, 48ч, 7 дней',
      'AI-генерация текста × 20',
      'Полная аналитика + экспорт',
      'Высокий приоритет',
    ],
  },
  {
    key: 'business',
    features: [
      'Безлимит кампаний',
      'Все 5 форматов (закрепы!)',
      'Безлимит AI-генерации',
      'API доступ',
      'Наивысший приоритет',
    ],
  },
]

export default function Plans() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading } = useMe()
  const { data: planDetails, isLoading: plansLoading } = usePlans()
  const purchasePlan = usePurchasePlan()

  const currentPlan = user?.plan ?? 'free'
  const currentInfo = PLAN_INFO[currentPlan]
  const balanceRub = Number(user?.balance_rub ?? 0)

  // Build price map from API data
  const planCostMap: Record<string, number> = {}
  if (planDetails) {
    for (const p of planDetails) {
      planCostMap[p.id] = p.price
    }
  }

  if (userLoading || plansLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-64" />)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Тарифы</h1>
        <p className="text-text-secondary mt-1">
          Текущий: {currentInfo.displayName} · Баланс: {balanceRub} ₽
        </p>
      </div>

      {balanceRub < 500 && (
        <Notification type="warning">
          Для смены тарифа нужен баланс.{' '}
          <button className="text-accent underline" onClick={() => navigate('/cabinet')}>
            Пополните баланс в кабинете
          </button>
        </Notification>
      )}

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {PLANS.map(({ key, features, featured }) => {
          const info = PLAN_INFO[key]
          const isCurrent = key === currentPlan
          const price = planCostMap[key] ?? 0

          return (
            <Card
              key={key}
              className={`p-5 flex flex-col ${
                featured ? 'ring-2 ring-accent shadow-lg' : ''
              } ${isCurrent ? 'bg-accent-muted/20' : ''}`}
            >
              {featured && (
                <span className="inline-block self-start px-2 py-0.5 rounded-full text-xs font-medium bg-accent text-accent-text mb-2">
                  Популярный
                </span>
              )}

              <div className="text-3xl mb-2">{info.emoji}</div>
              <h3 className="text-lg font-bold text-text-primary">{info.displayName}</h3>
              <p className="text-2xl font-bold text-text-primary mt-2">
                {price > 0 ? formatCurrency(price) : 'Бесплатно'}
              </p>
              {price > 0 && <p className="text-xs text-text-tertiary">₽/мес</p>}

              <ul className="space-y-2 mt-4 flex-1">
                {features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-text-secondary">
                    <span className="text-success mt-0.5">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-4">
                {isCurrent ? (
                  <span className="block w-full text-center py-2 rounded-md text-sm font-medium bg-accent-muted text-accent">
                    Ваш тариф
                  </span>
                ) : key === 'free' ? (
                  <Button
                    variant="secondary"
                    fullWidth
                    loading={purchasePlan.isPending}
                    onClick={() => purchasePlan.mutate('free')}
                  >
                    Перейти на Free
                  </Button>
                ) : (
                  <Button
                    variant={featured ? 'primary' : 'secondary'}
                    fullWidth
                    loading={purchasePlan.isPending}
                    onClick={() => purchasePlan.mutate(key)}
                  >
                    Выбрать {info.displayName}
                  </Button>
                )}
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
