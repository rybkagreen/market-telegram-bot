export const PLAN_INFO: Record<string, { displayName: string; emoji: string; aiGenerations: number; formats: string[] }> = {
  free: { displayName: 'Free', emoji: '🆓', aiGenerations: 0, formats: ['post_24h'] },
  starter: { displayName: 'Starter', emoji: '🚀', aiGenerations: 3, formats: ['post_24h', 'post_48h'] },
  pro: { displayName: 'Pro', emoji: '💎', aiGenerations: 20, formats: ['post_24h', 'post_48h', 'post_7d'] },
  business: { displayName: 'Agency', emoji: '🏢', aiGenerations: -1, formats: ['post_24h', 'post_48h', 'post_7d', 'pin_24h', 'pin_48h'] },
}

export const MIN_PRICE_PER_POST = 1000

// ──────────────── Financials (Промт 15.7) ────────────────
// Single source of truth: src/constants/fees.py.
// Effective rates MUST be derived from gross constants — никаких
// hardcoded 0.788 / 0.212 в screen-коде.
export const PLATFORM_COMMISSION_GROSS = 0.20
export const OWNER_SHARE_GROSS = 0.80
export const SERVICE_FEE = 0.015
export const OWNER_NET_RATE = OWNER_SHARE_GROSS * (1 - SERVICE_FEE)
export const PLATFORM_TOTAL_RATE = 1 - OWNER_NET_RATE
export const YOOKASSA_FEE = 0.035
export const PAYOUT_FEE = 0.015

/** Cancel split (after_confirmation): 50 / 40 / 10. */
export const CANCEL_REFUND_ADVERTISER = 0.50
export const CANCEL_REFUND_OWNER = 0.40
export const CANCEL_REFUND_PLATFORM = 0.10

/** Format a fraction as a localised percent string ("78,8%"). */
export function formatRatePct(rate: number, fractionDigits = 1): string {
  return `${(rate * 100).toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })}%`
}

/** Compute the placement-release split for a given price. */
export interface PlacementSplit {
  ownerGross: number
  serviceFee: number
  ownerNet: number
  platformGross: number
  platformTotal: number
}
export function computePlacementSplit(price: number): PlacementSplit {
  const ownerGross = price * OWNER_SHARE_GROSS
  const serviceFee = ownerGross * SERVICE_FEE
  const ownerNet = ownerGross - serviceFee
  const platformGross = price * PLATFORM_COMMISSION_GROSS
  const platformTotal = price - ownerNet
  return { ownerGross, serviceFee, ownerNet, platformGross, platformTotal }
}

export const CATEGORIES: { key: string; name: string; emoji: string }[] = [
  { key: 'business',      name: 'Бизнес',         emoji: '💼' },
  { key: 'it',            name: 'IT и технологии', emoji: '💻' },
  { key: 'marketing',     name: 'Маркетинг',      emoji: '📢' },
  { key: 'crypto',        name: 'Криптовалюта',   emoji: '₿' },
  { key: 'psychology',    name: 'Психология',     emoji: '🧠' },
  { key: 'health',        name: 'Здоровье',       emoji: '🏥' },
  { key: 'entertainment', name: 'Развлечения',    emoji: '🎭' },
  { key: 'travel',        name: 'Путешествия',    emoji: '✈️' },
  { key: 'food',          name: 'Еда',            emoji: '🍕' },
  { key: 'fashion',       name: 'Мода и стиль',   emoji: '👗' },
  { key: 'other',         name: 'Другое',         emoji: '🔹' },
]

export const PUBLICATION_FORMATS: Record<string, { name: string; description: string; icon: string; multiplier: number; minPlan: string }> = {
  post_24h: { name: 'Пост 24ч', description: 'Пост с удалением через 24 часа', icon: '📝', multiplier: 1.0, minPlan: 'free' },
  post_48h: { name: 'Пост 48ч', description: 'Пост с удалением через 48 часов', icon: '📝', multiplier: 1.4, minPlan: 'starter' },
  post_7d: { name: 'Пост 7д', description: 'Пост с удалением через 7 дней', icon: '📋', multiplier: 2.0, minPlan: 'pro' },
  pin_24h: { name: 'Закреп 24ч', description: 'Закреплённый пост на 24 часа', icon: '📌', multiplier: 3.0, minPlan: 'business' },
  pin_48h: { name: 'Закреп 48ч', description: 'Закреплённый пост на 48 часов', icon: '📌', multiplier: 4.0, minPlan: 'business' },
}

export function canUsePlan(userPlan: string, minPlan: string): boolean {
  const planOrder = ['free', 'starter', 'pro', 'business']
  const userIdx = planOrder.indexOf(userPlan)
  const minIdx = planOrder.indexOf(minPlan)
  return userPlan === 'admin' || userIdx >= minIdx
}

export function calcFormatPrice(basePrice: number, format: string): number {
  const fmt = PUBLICATION_FORMATS[format]
  if (!fmt) return basePrice
  return Math.round(basePrice * fmt.multiplier)
}

export function formatCurrency(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num)
}

export function formatCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
  return value.toString()
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

/**
 * Форматирование даты в GMT+3 (Москва).
 * Все даты на портале отображаются в московском времени.
 */
const MSK_TIMEZONE = 'Europe/Moscow'

export function formatDateTimeMSK(dt: string | null | undefined): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('ru-RU', {
    timeZone: MSK_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDateMSK(dt: string | null | undefined): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString('ru-RU', {
    timeZone: MSK_TIMEZONE,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatTimeMSK(dt: string | null | undefined): string {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('ru-RU', {
    timeZone: MSK_TIMEZONE,
    hour: '2-digit',
    minute: '2-digit',
  })
}
