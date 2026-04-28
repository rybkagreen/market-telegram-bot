// ============================================================
// RekHarbor Mini App — Business Constants
// Phase 3
// ============================================================

import type { Plan, PublicationFormat } from './types'

// ---- Publication formats ----

export const PUBLICATION_FORMATS: Record<
  PublicationFormat,
  { name: string; description: string; multiplier: number; icon: string; minPlan: Plan }
> = {
  post_24h: {
    name: 'Пост 24ч',
    description: 'Публикация + авто-удаление через 24 часа',
    multiplier: 1.0,
    icon: '📄',
    minPlan: 'free',
  },
  post_48h: {
    name: 'Пост 48ч',
    description: 'Публикация + авто-удаление через 48 часов',
    multiplier: 1.4,
    icon: '📄',
    minPlan: 'starter',
  },
  post_7d: {
    name: 'Пост 7 дней',
    description: 'Публикация + авто-удаление через 7 дней',
    multiplier: 2.0,
    icon: '📄',
    minPlan: 'pro',
  },
  pin_24h: {
    name: 'Закреп 24ч',
    description: 'Закрепляем + открепляем через 24 часа',
    multiplier: 3.0,
    icon: '📌',
    minPlan: 'business',
  },
  pin_48h: {
    name: 'Закреп 48ч',
    description: 'Закрепляем + открепляем через 48 часов',
    multiplier: 4.0,
    icon: '📌',
    minPlan: 'business',
  },
}

// ---- Plans ----

export const PLAN_HIERARCHY: Plan[] = ['free', 'starter', 'pro', 'business']

export const PLAN_INFO: Record<
  Plan,
  { displayName: string; price: number; maxCampaigns: number; aiGenerations: number }
> = {
  free:     { displayName: 'Free 🆓',     price: 0,    maxCampaigns: 1,  aiGenerations: 0  },
  starter:  { displayName: 'Starter 🚀',  price: 490,  maxCampaigns: 5,  aiGenerations: 3  },
  pro:      { displayName: 'Pro 💎',       price: 1490, maxCampaigns: 20, aiGenerations: 20 },
  business: { displayName: 'Agency 🏢',   price: 4990, maxCampaigns: -1, aiGenerations: -1 },
}

// ---- Financials (Промт 15.7) ----
// Single source of truth: src/constants/fees.py. Hardcoding effective
// rates (e.g. 0.788 / 0.212) anywhere else is a bug — derive them.
//
// Placement release split:
//   gross_owner    = price × OWNER_SHARE_GROSS
//   service_fee    = gross_owner × SERVICE_FEE
//   owner_net      = gross_owner − service_fee
//   platform_total = price − owner_net
export const PLATFORM_COMMISSION_GROSS = 0.20
export const OWNER_SHARE_GROSS = 0.80
export const SERVICE_FEE = 0.015
export const OWNER_NET_RATE = OWNER_SHARE_GROSS * (1 - SERVICE_FEE)
export const PLATFORM_TOTAL_RATE = 1 - OWNER_NET_RATE
// Legacy alias (some screens still import PLATFORM_COMMISSION) — points
// to the effective platform total under Промт 15.7.
export const PLATFORM_COMMISSION = PLATFORM_TOTAL_RATE
export const YOOKASSA_FEE = 0.035  // pass-through, platform earns 0
export const WITHDRAWAL_FEE = 0.015  // payout flow, separate from placement fees

/** Cancel split (after_confirmation): 50 / 40 / 10. */
export const CANCEL_REFUND_ADVERTISER = 0.50
export const CANCEL_REFUND_OWNER = 0.40
export const CANCEL_REFUND_PLATFORM = 0.10

/** Helpers: format a fraction (0.788) as a localised percent string ("78,8%"). */
export const formatRatePct = (rate: number, fractionDigits = 1): string =>
  `${(rate * 100).toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })}%`

/** Compute the placement-release split for a given price. */
export interface PlacementSplit {
  ownerGross: number
  serviceFee: number
  ownerNet: number
  platformGross: number
  platformTotal: number
}
export const computePlacementSplit = (price: number): PlacementSplit => {
  const ownerGross = price * OWNER_SHARE_GROSS
  const serviceFee = ownerGross * SERVICE_FEE
  const ownerNet = ownerGross - serviceFee
  const platformGross = price * PLATFORM_COMMISSION_GROSS
  const platformTotal = price - ownerNet
  return { ownerGross, serviceFee, ownerNet, platformGross, platformTotal }
}

export const MIN_TOPUP = 500
export const MAX_TOPUP = 300_000
export const MIN_WITHDRAWAL = 1_000
export const MIN_CAMPAIGN_BUDGET = 2_000
export const MIN_PRICE_PER_POST = 1_000

// ---- Business rules ----

export const MAX_COUNTER_OFFERS = 3
export const MAX_AD_TEXT_LENGTH = 1_000
export const MIN_REJECTION_COMMENT = 10
export const MIN_DISPUTE_COMMENT = 20
export const OWNER_RESPONSE_HOURS = 24
export const PAYMENT_TIMEOUT_HOURS = 24
export const DISPUTE_WINDOW_HOURS = 48
export const DISPUTE_AUTO_CLOSE_DAYS = 7

// ---- Categories ----

export const CATEGORIES = [
  { key: 'business',      name: 'Бизнес',              emoji: '💼' },
  { key: 'it',            name: 'IT и технологии',     emoji: '💻' },
  { key: 'marketing',     name: 'Маркетинг',           emoji: '📢' },
  { key: 'crypto',        name: 'Криптовалюта',        emoji: '₿' },
  { key: 'psychology',    name: 'Психология',          emoji: '🧠' },
  { key: 'health',        name: 'Здоровье',            emoji: '🏥' },
  { key: 'entertainment', name: 'Развлечения',         emoji: '🎭' },
  { key: 'travel',        name: 'Путешествия',         emoji: '✈️' },
  { key: 'food',          name: 'Еда',                 emoji: '🍕' },
  { key: 'fashion',       name: 'Мода и стиль',        emoji: '👗' },
  { key: 'other',         name: 'Другое',              emoji: '🔹' },
]

// ---- UI labels ----

export const PLACEMENT_STATUS_LABELS: Record<string, string> = {
  pending_owner:      'Ожидает владельца',
  counter_offer:      'Контр-предложение',
  pending_payment:    'Ожидает оплаты',
  escrow:             'На эскроу',
  published:          'Опубликовано',
  completed:          'Завершена',
  failed:             'Ошибка',
  failed_permissions: 'Нет прав',
  refunded:           'Возврат',
  cancelled:          'Отменено',
}

export const DISPUTE_REASON_LABELS: Record<string, string> = {
  // Backend (Telegram bot) reasons
  post_removed_early:  'Пост удалён раньше срока',
  bot_kicked:          'Бот удалён из канала',
  advertiser_complaint:'Жалоба рекламодателя',
  // Frontend (UI) reasons
  not_published:  'Пост не опубликован',
  wrong_time:     'Неправильное время публикации',
  wrong_text:     'Текст изменён без согласования',
  early_deletion: 'Пост удалён раньше срока',
  other:          'Другое',
}

// ============================================================
// Timezone-aware date formatting (GMT+3 / Europe/Moscow)
// All dates in the mini app display in Moscow time.
// ============================================================

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
