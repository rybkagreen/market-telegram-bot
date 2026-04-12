// ============================================================
// RekHarbor Mini App — Formatters
// Phase 3
// ============================================================

import type { Plan, PublicationFormat } from './types'
import { PLAN_HIERARCHY, PUBLICATION_FORMATS, YOOKASSA_FEE, WITHDRAWAL_FEE } from './constants'

// ---- Currency ----

const currencyFmt = new Intl.NumberFormat('ru-RU', {
  style: 'decimal',
  maximumFractionDigits: 0,
})

export function formatCurrency(amount: number | string): string {
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  if (!Number.isFinite(n)) return '0 ₽'
  return `${currencyFmt.format(n)} ₽`
}

export function formatNumber(n: number): string {
  return currencyFmt.format(n)
}

export function formatCompact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace('.0', '')}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace('.0', '')}K`
  return String(n)
}

export function formatPercent(n: number, decimals = 1): string {
  // if n > 1 — assume already a percentage value (e.g. 15 → "15%")
  const value = n > 1 ? n : n * 100
  return `${value.toFixed(decimals).replace(/\.0$/, '')}%`
}

// ---- Dates ----

const SHORT_MONTHS = [
  'янв', 'фев', 'мар', 'апр', 'май', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек',
]

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  return `${d.getDate()} ${SHORT_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  return `${d.getDate()} ${SHORT_MONTHS[d.getMonth()]}, ${d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`
}

export function formatRelativeTime(iso: string): string {
  const diff = new Date(iso).getTime() - Date.now()
  const abs = Math.abs(diff)
  const future = diff > 0

  const minutes = Math.floor(abs / 60_000)
  const hours = Math.floor(abs / 3_600_000)
  const days = Math.floor(abs / 86_400_000)

  let label: string
  if (days >= 1) label = `${days} ${pluralize(days, 'день', 'дня', 'дней')}`
  else if (hours >= 1) label = `${hours} ${pluralize(hours, 'час', 'часа', 'часов')}`
  else if (minutes >= 1) label = `${minutes} ${pluralize(minutes, 'минута', 'минуты', 'минут')}`
  else label = 'только что'

  if (label === 'только что') return label
  return future ? `через ${label}` : `${label} назад`
}

export function formatCountdown(iso: string): string {
  const ms = new Date(iso).getTime() - Date.now()
  if (ms <= 0) return '00:00:00'

  const totalSeconds = Math.floor(ms / 1000)
  const h = Math.floor(totalSeconds / 3600)
  const m = Math.floor((totalSeconds % 3600) / 60)
  const s = totalSeconds % 60

  return [h, m, s].map((v) => String(v).padStart(2, '0')).join(':')
}

// ---- Financial calculations ----

export function calcTopUpFee(desired: number): { desired: number; fee: number; total: number } {
  const fee = Math.round(desired * YOOKASSA_FEE)
  return { desired, fee, total: desired + fee }
}

export function calcWithdrawalFee(gross: number): { gross: number; fee: number; net: number } {
  const fee = Math.round(gross * WITHDRAWAL_FEE)
  return { gross, fee, net: gross - fee }
}

export function calcFormatPrice(
  basePrice: number | string,
  format: PublicationFormat,
): number {
  const base = typeof basePrice === 'string' ? parseFloat(basePrice) : basePrice
  return Math.round(base * PUBLICATION_FORMATS[format].multiplier)
}

// ---- Plan checks ----

export function canUsePlan(userPlan: Plan, requiredPlan: Plan): boolean {
  return PLAN_HIERARCHY.indexOf(userPlan) >= PLAN_HIERARCHY.indexOf(requiredPlan)
}

// ---- Helpers ----

function pluralize(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return one
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few
  return many
}
