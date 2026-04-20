import { useMemo, useState } from 'react'
import { Button, Skeleton, Notification, Icon, ScreenHeader } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useReferralStats } from '@/hooks/useUserQueries'
import type { ReferralItem } from '@/lib/types/misc'

interface LevelConfig {
  n: number
  name: string
  need: number
  pct: number
  color: string
  gradFrom: string
  gradTo: string
}

const LEVELS: LevelConfig[] = [
  { n: 1, name: 'Бронза', need: 0, pct: 5, color: 'text-warning', gradFrom: 'from-warning', gradTo: 'to-warning/70' },
  { n: 2, name: 'Серебро', need: 10, pct: 10, color: 'text-text-secondary', gradFrom: 'from-text-secondary', gradTo: 'to-text-secondary/70' },
  { n: 3, name: 'Золото', need: 30, pct: 15, color: 'text-warning', gradFrom: 'from-warning', gradTo: 'to-warning/70' },
  { n: 4, name: 'Платина', need: 60, pct: 20, color: 'text-accent-2', gradFrom: 'from-accent-2', gradTo: 'to-accent-2/70' },
]

interface ShareChannel {
  id: string
  label: string
  icon: IconName
}

const SHARE_CHANNELS: ShareChannel[] = [
  { id: 'tg', label: 'Telegram', icon: 'telegram' },
  { id: 'vk', label: 'VK', icon: 'external' },
  { id: 'whatsapp', label: 'WhatsApp', icon: 'chat' },
  { id: 'email', label: 'Email', icon: 'email' },
  { id: 'qr', label: 'QR-код', icon: 'share' },
]

function fmtRub(v: number) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(v)) + ' ₽'
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: 'long',
    timeZone: 'Europe/Moscow',
  })
}

function avatarChar(u: string | null, id: number) {
  if (u) return u[0].toUpperCase()
  return '#' + String(id).slice(-2)
}

function computeLevel(total: number): number {
  let lvl = 1
  for (const l of LEVELS) {
    if (total >= l.need) lvl = l.n
  }
  return lvl
}

export default function Referral() {
  const { data: stats, isLoading, isError } = useReferralStats()
  const [copiedCode, setCopiedCode] = useState(false)
  const [copiedLink, setCopiedLink] = useState(false)

  const copy = (text: string, setter: (v: boolean) => void) => {
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {})
    setter(true)
    setTimeout(() => setter(false), 1800)
  }

  const level = useMemo(() => computeLevel(stats?.total_referrals ?? 0), [stats?.total_referrals])
  const curLevel = LEVELS[level - 1]
  const nextLevel: LevelConfig | undefined = LEVELS[level]
  const progress = nextLevel
    ? Math.min(100, ((stats?.total_referrals ?? 0) / nextLevel.need) * 100)
    : 100

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-14" />
        <Skeleton className="h-52" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !stats) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить данные о рефералах</Notification>
      </div>
    )
  }

  const earned = Number(stats.total_earned_rub)

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Профиль', 'Реферальная программа']}
        title="Реферальная программа"
        subtitle="Приглашайте друзей — получайте бонусные кредиты с каждой оплаты"
        action={
          <Button variant="secondary" iconLeft="docs">
            Правила программы
          </Button>
        }
      />

      <div className="relative bg-gradient-to-br from-harbor-card via-harbor-card to-accent-muted border border-border rounded-2xl p-[22px] mb-5 overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />

        <div className="grid gap-5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
          <div>
            <div className="text-[11px] font-bold tracking-[0.09em] uppercase text-text-tertiary mb-2">
              Ваш реферальный код
            </div>

            <div className="flex items-center gap-2.5 py-3.5 px-4 bg-harbor-elevated border border-border rounded-[10px] mb-2.5">
              <code className="flex-1 font-mono text-lg font-semibold text-accent tracking-wider">
                {stats.referral_code}
              </code>
              <Button
                size="sm"
                variant={copiedCode ? 'primary' : 'secondary'}
                iconLeft={copiedCode ? 'check' : 'copy'}
                onClick={() => copy(stats.referral_code, setCopiedCode)}
              >
                {copiedCode ? 'Скопировано' : 'Копировать'}
              </Button>
            </div>

            <div className="flex items-center gap-2.5 py-2.5 px-3.5 bg-harbor-secondary border border-dashed border-border rounded-[10px]">
              <Icon name="external" size={14} className="text-text-tertiary" />
              <span className="flex-1 font-mono text-xs text-text-secondary truncate">
                {stats.referral_link}
              </span>
              <button
                onClick={() => copy(stats.referral_link, setCopiedLink)}
                className={`flex items-center gap-1 text-xs font-semibold transition-colors ${
                  copiedLink ? 'text-success' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                <Icon name={copiedLink ? 'check' : 'copy'} size={13} />
                {copiedLink ? 'Скопировано' : 'Копировать'}
              </button>
            </div>

            <div className="mt-3.5 flex gap-2 flex-wrap">
              {SHARE_CHANNELS.map((ch) => (
                <button
                  key={ch.id}
                  className="flex items-center gap-1.5 py-1.5 px-3 text-xs font-medium border border-border bg-harbor-elevated text-text-secondary rounded-2xl hover:border-accent hover:text-accent transition-colors"
                >
                  <Icon name={ch.icon} size={13} />
                  {ch.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[11px] font-bold tracking-[0.09em] uppercase text-text-tertiary mb-2">
              Ваш уровень
            </div>

            <div className="p-4 rounded-xl bg-harbor-secondary border border-border">
              <div className="flex items-center gap-3 mb-3.5">
                <div
                  className={`w-12 h-12 rounded-xl bg-gradient-to-br ${curLevel.gradFrom} ${curLevel.gradTo} grid place-items-center text-white shadow-lg`}
                >
                  <Icon name="star" size={22} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-display text-lg font-bold text-text-primary tracking-[-0.01em]">
                    {curLevel.name}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">
                    Бонус <span className={`${curLevel.color} font-semibold`}>{curLevel.pct}%</span> с каждой оплаты
                  </div>
                </div>
                {nextLevel && (
                  <div className="text-right text-[11px] text-text-tertiary">
                    До «{nextLevel.name}»
                    <br />
                    <span className="font-mono font-semibold text-text-primary text-[13px]">
                      {nextLevel.need - stats.total_referrals} чел.
                    </span>
                  </div>
                )}
              </div>

              <div className="relative h-2 rounded bg-harbor-elevated overflow-hidden mb-2.5">
                <div
                  className={`absolute inset-y-0 left-0 bg-gradient-to-r ${curLevel.gradFrom} ${nextLevel ? nextLevel.gradTo : curLevel.gradTo} rounded`}
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="grid grid-cols-4 gap-1.5">
                {LEVELS.map((lv) => {
                  const reached = stats.total_referrals >= lv.need
                  const current = level === lv.n
                  return (
                    <div
                      key={lv.n}
                      className={`py-1.5 px-1.5 pb-2 rounded-md text-center transition-all ${
                        current ? 'border border-accent/35' : 'border border-transparent'
                      } hover:bg-harbor-elevated`}
                    >
                      <div
                        className={`text-[9.5px] font-bold tracking-[0.06em] uppercase ${reached ? lv.color : 'text-text-tertiary'}`}
                      >
                        {lv.name}
                      </div>
                      <div
                        className={`font-mono text-[11px] mt-0.5 ${reached ? 'text-text-primary' : 'text-text-tertiary'}`}
                      >
                        {lv.need}+ · {lv.pct}%
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3.5 mb-5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <RefTile icon="users" tone="accent" label="Приглашено" value={stats.total_referrals} sub="всего за всё время" />
        <RefTile icon="check" tone="success" label="Активных" value={stats.active_referrals} sub="с первой оплатой" />
        <RefTile icon="ruble" tone="warning" label="Заработано" value={fmtRub(earned)} sub="зачислено на баланс" />
        <RefTile
          icon="zap"
          tone="accent2"
          label="Средний чек"
          value={fmtRub(earned / (stats.active_referrals || 1))}
          sub="с одного реферала"
        />
      </div>

      <div className="grid gap-4" style={{ gridTemplateColumns: 'minmax(0, 1.6fr) minmax(280px, 1fr)' }}>
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
          <div className="py-3.5 px-[18px] border-b border-border flex items-center justify-between">
            <div>
              <div className="font-display text-sm font-semibold text-text-primary">Ваши рефералы</div>
              <div className="text-xs text-text-tertiary mt-0.5">
                {stats.referrals.length} пользователей
              </div>
            </div>
          </div>
          {stats.referrals.length === 0 ? (
            <div className="p-[60px] text-center">
              <div className="inline-grid place-items-center w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary mb-3.5">
                <Icon name="users" size={22} />
              </div>
              <div className="font-display text-base font-semibold text-text-primary mb-1">
                Пока нет рефералов
              </div>
              <div className="text-[13px] text-text-secondary">Поделитесь ссылкой с друзьями</div>
            </div>
          ) : (
            stats.referrals.map((r, i) => (
              <RefRow key={r.id} r={r} isLast={i === stats.referrals.length - 1} />
            ))
          )}
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="font-display text-sm font-semibold text-text-primary mb-3.5">
            Как это работает
          </div>
          <ol className="list-none p-0 m-0 flex flex-col gap-3.5">
            {[
              { title: 'Поделитесь ссылкой', text: 'Отправьте код или ссылку другу любым удобным способом' },
              { title: 'Друг регистрируется', text: 'Достаточно перейти по ссылке и пройти регистрацию' },
              { title: 'Друг совершает оплату', text: 'Пополнение, тариф или эскроу — любой первый платёж' },
              { title: 'Вам начисляется бонус', text: 'Процент по уровню программы — мгновенно на баланс' },
            ].map((st, i) => (
              <li key={st.title} className="flex gap-3 items-start">
                <span
                  className={`w-[26px] h-[26px] rounded-[7px] grid place-items-center font-display font-bold text-xs flex-shrink-0 ${
                    i === 0 ? 'bg-accent text-white' : 'bg-accent-muted text-accent'
                  }`}
                >
                  {i + 1}
                </span>
                <div>
                  <div className="text-[13px] font-semibold text-text-primary">{st.title}</div>
                  <div className="text-xs text-text-secondary leading-relaxed mt-0.5">{st.text}</div>
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-[18px] p-3 bg-accent-muted rounded-lg border border-accent/15 flex gap-2.5 items-start">
            <Icon name="info" size={14} className="text-accent mt-0.5 flex-shrink-0" />
            <div className="text-xs text-text-secondary leading-[1.5]">
              Без ограничений — приглашайте сколько угодно. Бонусы начисляются со всех будущих платежей реферала.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const tileIconBg: Record<'accent' | 'success' | 'warning' | 'accent2', string> = {
  accent: 'bg-accent-muted text-accent',
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function RefTile({
  icon,
  tone,
  label,
  value,
  sub,
}: {
  icon: IconName
  tone: 'accent' | 'success' | 'warning' | 'accent2'
  label: string
  value: string | number
  sub: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-4 flex gap-3 items-start">
      <span className={`grid place-items-center w-[38px] h-[38px] rounded-[9px] flex-shrink-0 ${tileIconBg[tone]}`}>
        <Icon name={icon} size={16} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
          {label}
        </div>
        <div className="font-display text-xl font-bold text-text-primary tracking-[-0.02em] tabular-nums truncate">
          {value}
        </div>
        <div className="text-[11.5px] text-text-tertiary mt-0.5">{sub}</div>
      </div>
    </div>
  )
}

function RefRow({ r, isLast }: { r: ReferralItem; isLast: boolean }) {
  return (
    <div
      className={`grid gap-3.5 items-center py-3 px-[18px] ${isLast ? '' : 'border-b border-border'}`}
      style={{ gridTemplateColumns: '36px 1fr auto' }}
    >
      <div
        className={`w-8 h-8 rounded-lg grid place-items-center font-display font-bold text-xs ${
          r.is_active
            ? 'bg-gradient-to-br from-accent to-accent-2 text-white'
            : 'bg-harbor-elevated text-text-tertiary'
        }`}
      >
        {avatarChar(r.username, r.telegram_id)}
      </div>
      <div className="min-w-0">
        <div className="text-[13px] font-semibold text-text-primary truncate">
          {r.username ? '@' + r.username : `User #${r.telegram_id}`}
        </div>
        <div className="text-[11px] text-text-tertiary mt-0.5">
          Присоединился {fmtDate(r.created_at)}
        </div>
      </div>
      <span
        className={`inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase py-1 px-2 rounded ${
          r.is_active ? 'bg-success-muted text-success' : 'bg-harbor-elevated text-text-tertiary'
        }`}
      >
        <span className={`w-1 h-1 rounded-full ${r.is_active ? 'bg-success' : 'bg-text-tertiary'}`} />
        {r.is_active ? 'Активен' : 'Новый'}
      </span>
    </div>
  )
}
