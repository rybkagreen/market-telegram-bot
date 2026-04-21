import { useMemo, useState } from 'react'
import { Skeleton, Notification, Icon, ScreenHeader, Button, Sparkline } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useReputationHistory } from '@/hooks/useReputationQueries'
import type { ReputationHistoryItem } from '@/lib/types/analytics'

type Tone = 'pos' | 'neg' | 'neu'

interface ActionMeta {
  label: string
  icon: IconName
  tone: Tone
}

const ACTION_META: Record<string, ActionMeta> = {
  placement_completed: { label: 'Размещение завершено', icon: 'check', tone: 'pos' },
  placement_cancelled: { label: 'Размещение отменено', icon: 'refresh', tone: 'neg' },
  review_positive: { label: 'Положительный отзыв', icon: 'star', tone: 'pos' },
  review_negative: { label: 'Отрицательный отзыв', icon: 'warning', tone: 'neg' },
  dispute_won: { label: 'Спор выигран', icon: 'lock', tone: 'pos' },
  dispute_lost: { label: 'Спор проигран', icon: 'lock', tone: 'neg' },
  dispute_resolved: { label: 'Спор решён', icon: 'disputes', tone: 'neu' },
  violation: { label: 'Нарушение правил', icon: 'warning', tone: 'neg' },
  timeout: { label: 'Нарушение сроков', icon: 'clock', tone: 'neg' },
  bonus: { label: 'Бонус', icon: 'zap', tone: 'pos' },
}

const ROLE_LABELS: Record<string, string> = {
  advertiser: 'Рекламодатель',
  owner: 'Владелец канала',
}

type RoleFilter = 'all' | 'advertiser' | 'owner'
type ToneFilter = 'all' | 'pos' | 'neg'

const ROLE_FILTERS: { id: RoleFilter; label: string }[] = [
  { id: 'all', label: 'Все роли' },
  { id: 'advertiser', label: 'Рекламодатель' },
  { id: 'owner', label: 'Владелец' },
]

const TONE_FILTERS: { id: ToneFilter; label: string }[] = [
  { id: 'all', label: 'Все' },
  { id: 'pos', label: 'Плюсы' },
  { id: 'neg', label: 'Минусы' },
]

function fmtDateTime(iso: string) {
  const d = new Date(iso)
  return d
    .toLocaleString('ru-RU', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Europe/Moscow',
    })
    .replace(',', ' ·')
}

function dayKey(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: 'long',
    timeZone: 'Europe/Moscow',
  })
}

function getMeta(action: string): ActionMeta {
  return ACTION_META[action] ?? { label: action, icon: 'docs', tone: 'neu' }
}

export default function ReputationHistory() {
  const [roleFilter, setRoleFilter] = useState<RoleFilter>('all')
  const [toneFilter, setToneFilter] = useState<ToneFilter>('all')
  const { data: items, isLoading, isError } = useReputationHistory(50, 0)

  const list = items ?? []

  const filtered = useMemo(() => {
    return list.filter((e) => {
      if (roleFilter !== 'all' && e.role !== roleFilter) return false
      const tone = getMeta(e.action).tone
      if (toneFilter === 'pos' && tone !== 'pos') return false
      if (toneFilter === 'neg' && tone !== 'neg') return false
      return true
    })
  }, [list, roleFilter, toneFilter])

  const groups = useMemo(() => {
    const m = new Map<string, ReputationHistoryItem[]>()
    for (const e of filtered) {
      const k = dayKey(e.created_at)
      const arr = m.get(k) ?? []
      arr.push(e)
      m.set(k, arr)
    }
    return Array.from(m.entries())
  }, [filtered])

  const advertiser = list.filter((r) => r.role === 'advertiser')
  const owner = list.filter((r) => r.role === 'owner')

  const advScore = advertiser[0]?.score_after ?? 0
  const advPrev = advertiser[advertiser.length - 1]?.score_before ?? advScore
  const ownScore = owner[0]?.score_after ?? 0
  const ownPrev = owner[owner.length - 1]?.score_before ?? ownScore

  const advTrend = advertiser
    .slice()
    .reverse()
    .map((r) => r.score_after)
  const ownTrend = owner
    .slice()
    .reverse()
    .map((r) => r.score_after)

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-14" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-44" />
          <Skeleton className="h-44" />
        </div>
        <Skeleton className="h-16" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить историю репутации</Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="История репутации"
        subtitle="События, повлиявшие на ваш рейтинг рекламодателя и владельца канала"
        action={
          <Button variant="secondary" size="sm" iconLeft="docs">
            Правила рейтинга
          </Button>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <ScoreCard
          role="Рекламодатель"
          icon="cabinet"
          accent="accent"
          score={advScore}
          prev={advPrev}
          trend={advTrend}
          events={advertiser.length}
          tier={advScore >= 4.5 ? 'Gold' : advScore >= 3.5 ? 'Silver' : 'Bronze'}
          tierNext={advScore >= 4.5 ? 'Platinum at 4.85' : 'Gold at 4.50'}
        />
        <ScoreCard
          role="Владелец канала"
          icon="channels"
          accent="accent2"
          score={ownScore}
          prev={ownPrev}
          trend={ownTrend}
          events={owner.length}
          tier={ownScore >= 4.8 ? 'Platinum' : ownScore >= 4.5 ? 'Gold' : 'Silver'}
          tierNext={ownScore >= 4.8 ? 'Diamond at 4.95' : 'Platinum at 4.80'}
        />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3.5 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-tertiary font-medium">Роль:</span>
          <div className="flex p-[3px] rounded-lg bg-harbor-elevated border border-border">
            {ROLE_FILTERS.map((r) => {
              const on = roleFilter === r.id
              return (
                <button
                  key={r.id}
                  onClick={() => setRoleFilter(r.id)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-[5px] transition-colors ${
                    on ? 'bg-harbor-card text-text-primary' : 'text-text-secondary'
                  }`}
                >
                  {r.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-tertiary font-medium">Эффект:</span>
          <div className="flex gap-1.5">
            {TONE_FILTERS.map((t) => {
              const on = toneFilter === t.id
              const toneClass =
                t.id === 'pos'
                  ? on
                    ? 'border-success bg-success-muted text-success'
                    : 'border-border text-text-secondary'
                  : t.id === 'neg'
                    ? on
                      ? 'border-danger bg-danger-muted text-danger'
                      : 'border-border text-text-secondary'
                    : on
                      ? 'border-accent bg-accent-muted text-accent'
                      : 'border-border text-text-secondary'
              return (
                <button
                  key={t.id}
                  onClick={() => setToneFilter(t.id)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-2xl border transition-all ${toneClass}`}
                >
                  {t.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex-1" />

        <div className="text-xs text-text-tertiary font-mono tabular-nums">
          {filtered.length} событий
        </div>
      </div>

      {groups.length === 0 ? (
        <div className="bg-harbor-card border border-dashed border-border rounded-xl p-[60px] text-center">
          <div className="inline-grid place-items-center w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary mb-3.5">
            <Icon name="star" size={22} />
          </div>
          <div className="font-display text-base font-semibold text-text-primary mb-1">
            История пуста
          </div>
          <div className="text-[13px] text-text-secondary">
            Пока нет событий, повлиявших на репутацию
          </div>
        </div>
      ) : (
        groups.map(([day, items]) => (
          <div key={day} className="mb-6">
            <div className="text-[11px] font-bold uppercase tracking-[0.09em] text-text-tertiary py-2 px-0.5 pb-2.5 flex items-center gap-2.5">
              <span>{day}</span>
              <span className="flex-1 h-px bg-border" />
            </div>
            <div className="flex flex-col gap-2.5">
              {items.map((e) => (
                <RepRow key={e.id} item={e} />
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}

const accentIconBg: Record<'accent' | 'accent2', string> = {
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
}

const accentStripe: Record<'accent' | 'accent2', string> = {
  accent: 'from-accent to-accent/55',
  accent2: 'from-accent-2 to-accent-2/55',
}

const accentProgress: Record<'accent' | 'accent2', string> = {
  accent: 'from-accent to-accent/80',
  accent2: 'from-accent-2 to-accent-2/80',
}

const accentText: Record<'accent' | 'accent2', string> = {
  accent: 'text-accent',
  accent2: 'text-accent-2',
}

function ScoreCard({
  role,
  icon,
  accent,
  score,
  prev,
  trend,
  events,
  tier,
  tierNext,
}: {
  role: string
  icon: IconName
  accent: 'accent' | 'accent2'
  score: number
  prev: number
  trend: number[]
  events: number
  tier: string
  tierNext: string
}) {
  const diff = score - prev
  const up = diff >= 0
  const pct = Math.min((score / 5) * 100, 100)

  return (
    <div className="relative bg-harbor-card border border-border rounded-2xl py-5 px-[22px] overflow-hidden">
      <div className={`absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r ${accentStripe[accent]}`} />

      <div className="flex items-start gap-3.5 mb-3.5">
        <div
          className={`w-10 h-10 rounded-[10px] grid place-items-center flex-shrink-0 ${accentIconBg[accent]}`}
        >
          <Icon name={icon} size={19} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-display text-sm font-semibold text-text-primary">{role}</div>
          <div className="text-[11px] text-text-tertiary mt-0.5 flex items-center gap-1.5">
            <Icon name="star" size={11} className={accentText[accent]} />
            <span className={`${accentText[accent]} font-semibold`}>{tier}</span>
            <span className="text-text-tertiary">· {tierNext}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="font-display text-4xl font-bold text-text-primary tracking-[-0.03em] leading-none tabular-nums">
            {score.toFixed(2)}
          </div>
          <div
            className={`inline-flex items-center gap-0.5 mt-1.5 text-[11px] font-semibold font-mono tabular-nums ${
              up ? 'text-success' : 'text-danger'
            }`}
          >
            <Icon name={up ? 'arrow-up' : 'arrow-down'} size={11} strokeWidth={2} />
            {up ? '+' : ''}
            {diff.toFixed(2)}
          </div>
        </div>
      </div>

      <div className="h-1.5 rounded-sm bg-harbor-elevated overflow-hidden mb-3.5">
        <div
          className={`h-full rounded-sm bg-gradient-to-r ${accentProgress[accent]}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 text-[11.5px] text-text-tertiary">
          <span>{events} событий</span>
          <span className="opacity-50">·</span>
          <span>30 дней</span>
        </div>
        <Sparkline
          data={trend.length > 1 ? trend : [0, 0]}
          width={160}
          height={32}
          className={accentText[accent]}
        />
      </div>
    </div>
  )
}

const toneClass: Record<Tone, { border: string; iconBg: string; iconFg: string }> = {
  pos: { border: 'border-l-success', iconBg: 'bg-success-muted', iconFg: 'text-success' },
  neg: { border: 'border-l-danger', iconBg: 'bg-danger-muted', iconFg: 'text-danger' },
  neu: { border: 'border-l-text-secondary', iconBg: 'bg-harbor-elevated', iconFg: 'text-text-secondary' },
}

const deltaPillClass: Record<'pos' | 'neg' | 'zero', string> = {
  pos: 'bg-success-muted text-success border-success/15',
  neg: 'bg-danger-muted text-danger border-danger/15',
  zero: 'bg-harbor-elevated text-text-tertiary border-border',
}

function RepRow({ item }: { item: ReputationHistoryItem }) {
  const meta = getMeta(item.action)
  const tc = toneClass[meta.tone]
  const dPolarity: 'pos' | 'neg' | 'zero' = item.delta > 0 ? 'pos' : item.delta < 0 ? 'neg' : 'zero'
  const dText = item.delta > 0 ? `+${item.delta.toFixed(2)}` : item.delta.toFixed(2)

  const roleAccent =
    item.role === 'advertiser'
      ? 'bg-accent-muted text-accent'
      : 'bg-accent-2-muted text-accent-2'

  return (
    <div
      className={`bg-harbor-card border border-border border-l-[3px] rounded-[10px] py-3.5 pl-4 pr-[18px] grid gap-3.5 items-center transition-colors hover:border-border-active ${tc.border}`}
      style={{ gridTemplateColumns: '42px 1fr auto 130px' }}
    >
      <span
        className={`w-[38px] h-[38px] rounded-[10px] grid place-items-center border border-transparent ${tc.iconBg} ${tc.iconFg}`}
      >
        <Icon name={meta.icon} size={17} />
      </span>

      <div className="min-w-0">
        <div className="flex items-center gap-2.5 mb-0.5 flex-wrap">
          <span className="text-[13.5px] font-semibold text-text-primary">{meta.label}</span>
          <span
            className={`text-[10px] font-bold tracking-[0.08em] uppercase py-0.5 px-[7px] rounded ${roleAccent}`}
          >
            {ROLE_LABELS[item.role] ?? item.role}
          </span>
        </div>
        {item.comment && (
          <div className="text-[12.5px] text-text-secondary leading-[1.45] line-clamp-2">
            {item.comment}
          </div>
        )}
        <div className="text-[11px] text-text-tertiary mt-1 tabular-nums">
          {fmtDateTime(item.created_at)} МСК
        </div>
      </div>

      <span
        className={`font-mono tabular-nums text-sm font-bold py-1.5 px-2.5 rounded-lg border whitespace-nowrap ${deltaPillClass[dPolarity]}`}
      >
        {dText}
      </span>

      <div className="flex items-center gap-1.5 font-mono text-xs tabular-nums text-text-secondary whitespace-nowrap">
        <span className="text-text-tertiary">{item.score_before.toFixed(2)}</span>
        <Icon name="arrow-right" size={11} className="text-text-tertiary" />
        <span className="text-text-primary font-semibold">{item.score_after.toFixed(2)}</span>
      </div>
    </div>
  )
}
