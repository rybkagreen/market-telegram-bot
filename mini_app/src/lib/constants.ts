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

// ---- Financials ----

export const PLATFORM_COMMISSION = 0.15
export const YOOKASSA_FEE = 0.035
export const WITHDRAWAL_FEE = 0.015

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
