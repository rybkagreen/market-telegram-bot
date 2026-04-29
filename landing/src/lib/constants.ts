// Промт 15.7. Source of truth: src/constants/fees.py. Effective rates
// MUST be derived from gross constants — no hardcoded 0.788/0.212.
export const PLATFORM_COMMISSION_GROSS = 0.20
export const OWNER_SHARE_GROSS = 0.80
export const SERVICE_FEE = 0.015
export const OWNER_NET_RATE = OWNER_SHARE_GROSS * (1 - SERVICE_FEE)
export const PLATFORM_COMMISSION_EFFECTIVE = 1 - OWNER_NET_RATE
export const OWNER_SHARE_EFFECTIVE = OWNER_NET_RATE
// Legacy alias kept for backwards-compat with imports.
export const PLATFORM_COMMISSION = PLATFORM_COMMISSION_EFFECTIVE
export const YOOKASSA_FEE = 0.035
export const PAYOUT_FEE = 0.015
export const CANCEL_REFUND_ADVERTISER = 0.50

export const formatRatePct = (rate: number, fractionDigits = 1): string =>
  `${(rate * 100).toLocaleString('ru-RU', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })}%`

export const TARIFFS = [
  {
    id: 'free',
    displayName: 'Free',
    priceRub: 0,
    features: ['До 3 каналов', 'Базовая аналитика', 'Email поддержка'],
  },
  {
    id: 'starter',
    displayName: 'Starter',
    priceRub: 490,
    features: ['До 10 каналов', 'Расширенная аналитика', 'Приоритетная поддержка'],
  },
  {
    id: 'pro',
    displayName: 'Pro',
    priceRub: 1490,
    features: ['До 50 каналов', 'AI генерация текстов', 'Персональный менеджер'],
  },
  {
    id: 'business',
    displayName: 'Agency',  // displays as "Agency", stored as "business"
    priceRub: 4990,
    features: ['Неограниченно каналов', 'White-label', 'SLA 99.9%'],
  },
] as const

export const AD_FORMATS = [
  { id: 'post', label: 'Рекламный пост' },
  { id: 'stories', label: 'Stories' },
  { id: 'repost', label: 'Репост' },
] as const

export const SITE_URL = 'https://rekharbor.ru'
export const BOT_URL = 'https://t.me/RekHarborBot'
export const PORTAL_URL = 'https://portal.rekharbor.ru'
