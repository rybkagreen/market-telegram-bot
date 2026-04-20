import { Fragment } from 'react'
import { useNavigate } from 'react-router-dom'
import { Notification, Button, Skeleton, Icon, ScreenHeader, LinkButton } from '@shared/ui'
import { useMe } from '@/hooks/queries'
import { usePlans, usePurchasePlan } from '@/hooks/useBillingQueries'
import type { Plan } from '@/lib/types'

type PlanAccent = 'muted' | 'info' | 'accent' | 'accent2'

interface PlanConfig {
  key: Plan
  name: string
  glyph: string
  tagline: string
  accent: PlanAccent
  featured?: boolean
  features: string[]
}

const PLAN_DATA: PlanConfig[] = [
  {
    key: 'free',
    name: 'Free',
    glyph: 'F',
    tagline: 'Для знакомства с платформой',
    accent: 'muted',
    features: ['1 активная кампания', 'Только пост 24ч', 'Базовая аналитика'],
  },
  {
    key: 'starter',
    name: 'Starter',
    glyph: 'S',
    tagline: 'Для первых кампаний',
    accent: 'info',
    features: [
      '5 активных кампаний',
      'Пост 24ч и 48ч',
      'AI-генерация × 3',
      'Расширенная аналитика',
    ],
  },
  {
    key: 'pro',
    name: 'Pro',
    glyph: 'P',
    tagline: 'Для регулярных размещений',
    accent: 'accent',
    featured: true,
    features: [
      '20 активных кампаний',
      'Пост 24ч, 48ч и 7 дней',
      'AI-генерация × 20',
      'Полная аналитика + экспорт',
      'Высокий приоритет в ленте',
    ],
  },
  {
    key: 'business',
    name: 'Agency',
    glyph: 'A',
    tagline: 'Для агентств и команд',
    accent: 'accent2',
    features: [
      'Безлимит кампаний',
      'Все 5 форматов (закрепы)',
      'Безлимит AI-генерации',
      'API-доступ',
      'Наивысший приоритет',
    ],
  },
]

type ComparisonValue = string | boolean

const COMPARISON_ROWS: { label: string; values: ComparisonValue[] }[] = [
  { label: 'Активных кампаний', values: ['1', '5', '20', '∞'] },
  { label: 'Пост 24 часа', values: [true, true, true, true] },
  { label: 'Пост 48 часов', values: [false, true, true, true] },
  { label: 'Пост 7 дней', values: [false, false, true, true] },
  { label: 'Закрепы', values: [false, false, false, true] },
  { label: 'AI-генерация текста', values: ['—', '× 3', '× 20', '∞'] },
  { label: 'Экспорт аналитики', values: [false, false, true, true] },
  { label: 'API-доступ', values: [false, false, false, true] },
  {
    label: 'Приоритет поддержки',
    values: ['Обычный', 'Обычный', 'Высокий', 'Наивысший'],
  },
]

function fmtRub(v: number) {
  return new Intl.NumberFormat('ru-RU').format(v) + ' ₽'
}

const glyphBgClass: Record<PlanAccent, string> = {
  muted: 'bg-[oklch(0.40_0.05_260)] text-white',
  info: 'bg-info text-white',
  accent: 'bg-accent text-white',
  accent2: 'bg-accent-2 text-white',
}

const checkBgClass: Record<PlanAccent, string> = {
  muted: 'bg-harbor-elevated text-text-secondary',
  info: 'bg-info-muted text-info',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
}

export default function Plans() {
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading } = useMe()
  const { data: planDetails, isLoading: plansLoading } = usePlans()
  const purchasePlan = usePurchasePlan()

  const currentPlan: Plan = (user?.plan as Plan | undefined) ?? 'free'
  const balanceRub = Number(user?.balance_rub ?? 0)

  const priceMap: Record<string, number> = {}
  if (planDetails) {
    for (const p of planDetails) priceMap[p.id] = p.price
  }

  const currentName = PLAN_DATA.find((p) => p.key === currentPlan)?.name ?? 'Free'

  if (userLoading || plansLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-5">
        <Skeleton className="h-14" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-80" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Тарифы"
        subtitle={
          <>
            Текущий план:{' '}
            <span className="text-accent font-semibold">{currentName}</span>
            <span className="mx-2.5 text-text-tertiary">·</span>
            Баланс:{' '}
            <span className="font-mono font-medium text-text-primary">{fmtRub(balanceRub)}</span>
          </>
        }
        action={
          <Button variant="secondary" iconLeft="topup" onClick={() => navigate('/topup')}>
            Пополнить баланс
          </Button>
        }
      />

      {balanceRub < 500 && (
        <div className="mb-5">
          <Notification type="warning">
            Для смены тарифа нужен баланс.{' '}
            <LinkButton underline onClick={() => navigate('/topup')}>
              Пополните баланс
            </LinkButton>{' '}
            в кабинете.
          </Notification>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
        {PLAN_DATA.map((plan) => (
          <PlanCard
            key={plan.key}
            plan={plan}
            price={priceMap[plan.key] ?? 0}
            isCurrent={plan.key === currentPlan}
            loading={purchasePlan.isPending}
            onSelect={() => purchasePlan.mutate(plan.key)}
          />
        ))}
      </div>

      <ComparisonTable currentPlan={currentPlan} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
        <FaqCell
          icon="refresh"
          title="Смена тарифа"
          text="Списание в момент активации нового тарифа. Неиспользованные дни прошлого плана пересчитываются."
        />
        <FaqCell
          icon="lock"
          title="Отмена"
          text="Можно отменить автопродление в любой момент. План будет действовать до конца оплаченного периода."
        />
        <FaqCell
          icon="zap"
          title="Скидки"
          text="При оплате на 3 месяца — −10%, на 6 месяцев — −15%, на год — −20%."
        />
      </div>
    </div>
  )
}

interface PlanCardProps {
  plan: PlanConfig
  price: number
  isCurrent: boolean
  loading: boolean
  onSelect: () => void
}

function PlanCard({ plan, price, isCurrent, loading, onSelect }: PlanCardProps) {
  const { name, glyph, tagline, accent, featured, features } = plan
  const isPaid = price > 0

  const borderClass = featured
    ? 'border-accent/35 shadow-[0_0_0_1px_var(--color-accent)]/20'
    : 'border-border'

  return (
    <div
      className={`relative bg-harbor-card border rounded-xl pt-[22px] px-5 pb-5 flex flex-col overflow-hidden transition-transform duration-fast hover:-translate-y-0.5 ${borderClass}`}
    >
      {featured && (
        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />
      )}

      <div className="flex items-start justify-between mb-3.5">
        <div
          className={`w-11 h-11 rounded-[10px] grid place-items-center font-display text-xl font-bold tracking-[-0.02em] ${glyphBgClass[accent]}`}
        >
          {glyph}
        </div>
        {featured && !isCurrent && (
          <span className="text-[10px] font-bold tracking-[0.08em] uppercase px-2 py-1 rounded bg-accent-muted text-accent">
            Популярный
          </span>
        )}
        {isCurrent && (
          <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-[0.08em] uppercase px-2 py-1 rounded bg-success-muted text-success">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            Активен
          </span>
        )}
      </div>

      <div className="font-display text-[22px] font-bold tracking-[-0.02em] text-text-primary leading-tight">
        {name}
      </div>
      <div className="text-[12.5px] text-text-tertiary mt-0.5 mb-4">{tagline}</div>

      <div className="mb-[18px]">
        {isPaid ? (
          <>
            <span className="font-display text-[32px] font-bold tracking-[-0.03em] text-text-primary">
              {new Intl.NumberFormat('ru-RU').format(price)}
            </span>
            <span className="text-[13px] text-text-secondary ml-1">₽ / мес</span>
          </>
        ) : (
          <span className="font-display text-[28px] font-bold tracking-[-0.02em] text-text-primary">
            Бесплатно
          </span>
        )}
      </div>

      <div className="h-px bg-border -mx-5 mb-4" />

      <ul className="list-none p-0 m-0 flex flex-col gap-[9px] flex-1">
        {features.map((f) => (
          <li
            key={f}
            className="flex gap-[9px] items-start text-[13px] leading-[1.45] text-text-secondary"
          >
            <span
              className={`mt-0.5 grid place-items-center w-3.5 h-3.5 rounded-full flex-shrink-0 ${checkBgClass[accent]}`}
            >
              <Icon name="check" size={9} strokeWidth={2.5} />
            </span>
            <span>{f}</span>
          </li>
        ))}
      </ul>

      <div className="mt-5">
        {isCurrent ? (
          <div className="py-2.5 px-4 rounded-lg text-center bg-success-muted text-success text-[13px] font-semibold border border-dashed border-success/35">
            Ваш тариф
          </div>
        ) : (
          <Button
            variant={featured ? 'primary' : 'secondary'}
            fullWidth
            loading={loading}
            onClick={onSelect}
          >
            {price === 0 ? 'Перейти на Free' : `Выбрать ${name}`}
          </Button>
        )}
      </div>
    </div>
  )
}

function ComparisonTable({ currentPlan }: { currentPlan: Plan }) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
      <div className="px-[22px] py-4 border-b border-border flex items-center justify-between">
        <div>
          <div className="font-display text-[15px] font-semibold text-text-primary">
            Сравнение возможностей
          </div>
          <div className="text-xs text-text-tertiary mt-0.5">
            Все тарифы включают доступ к маркетплейсу и авто-модерацию
          </div>
        </div>
        <span className="text-[11px] text-text-tertiary flex items-center gap-1.5">
          <Icon name="info" size={13} />
          Цены указаны без НДС
        </span>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.6fr repeat(4, 1fr)' }}>
        <div className="px-[22px] py-3.5 border-b border-border bg-harbor-secondary" />
        {PLAN_DATA.map((plan) => {
          const active = plan.key === currentPlan
          return (
            <div
              key={plan.key}
              className={`px-4 py-3.5 border-b border-l border-border text-center ${active ? 'bg-accent-muted' : 'bg-harbor-secondary'}`}
            >
              <div
                className={`font-display text-[13px] font-semibold ${active ? 'text-accent' : 'text-text-primary'}`}
              >
                {plan.name}
              </div>
            </div>
          )
        })}

        {COMPARISON_ROWS.map((row, ri) => {
          const isLast = ri === COMPARISON_ROWS.length - 1
          return (
            <Fragment key={ri}>
              <div
                className={`px-[22px] py-[13px] text-[13px] text-text-secondary ${isLast ? '' : 'border-b border-border'}`}
              >
                {row.label}
              </div>
              {row.values.map((v, vi) => {
                const planKey = PLAN_DATA[vi].key
                const active = planKey === currentPlan
                const isNumeric = typeof v === 'string' && /[∞×0-9]/.test(v)
                return (
                  <div
                    key={vi}
                    className={`px-4 py-[13px] border-l border-border text-center text-[13px] ${
                      isLast ? '' : 'border-b'
                    } ${active ? 'bg-accent-muted/40' : 'bg-transparent'}`}
                  >
                    {v === true && (
                      <Icon
                        name="check"
                        size={14}
                        strokeWidth={2.2}
                        className="text-success inline-block"
                      />
                    )}
                    {v === false && (
                      <span className="text-text-tertiary text-base">—</span>
                    )}
                    {typeof v === 'string' && (
                      <span
                        className={`${
                          isNumeric ? 'font-mono font-medium' : ''
                        } text-text-primary`}
                      >
                        {v}
                      </span>
                    )}
                  </div>
                )
              })}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
}

function FaqCell({
  icon,
  title,
  text,
}: {
  icon: 'refresh' | 'lock' | 'zap'
  title: string
  text: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-[10px] p-[18px]">
      <div className="flex items-center gap-2.5 mb-2">
        <span className="grid place-items-center w-7 h-7 rounded-[7px] bg-accent-muted text-accent">
          <Icon name={icon} size={14} />
        </span>
        <div className="font-display text-[13.5px] font-semibold text-text-primary">
          {title}
        </div>
      </div>
      <div className="text-[12.5px] leading-[1.55] text-text-secondary">{text}</div>
    </div>
  )
}
