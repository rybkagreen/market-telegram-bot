// ============================================================
// RekHarbor Mini App — Zod Validation Schemas
// Phase 3
// ============================================================

import { z } from 'zod'
import {
  MIN_TOPUP,
  MAX_TOPUP,
  MIN_WITHDRAWAL,
  MIN_PRICE_PER_POST,
  MAX_AD_TEXT_LENGTH,
  MIN_REJECTION_COMMENT,
  MIN_DISPUTE_COMMENT,
} from './constants'

export const topUpSchema = z.object({
  amount: z.number().min(MIN_TOPUP, `Минимальная сумма ${MIN_TOPUP} ₽`).max(MAX_TOPUP, `Максимальная сумма ${MAX_TOPUP} ₽`),
})

export const withdrawalSchema = z.object({
  gross_amount: z.number().min(MIN_WITHDRAWAL, `Минимальная сумма вывода ${MIN_WITHDRAWAL} ₽`),
  requisites: z.string().min(5, 'Укажите реквизиты (мин. 5 символов)'),
})

export const adTextSchema = z
  .string()
  .min(10, 'Текст рекламы — минимум 10 символов')
  .max(MAX_AD_TEXT_LENGTH, `Максимум ${MAX_AD_TEXT_LENGTH} символов`)

export const rejectionSchema = z
  .string()
  .min(MIN_REJECTION_COMMENT, `Комментарий — минимум ${MIN_REJECTION_COMMENT} символов`)
  .refine(
    (val) => /[а-яА-Яa-zA-Z]{3,}/.test(val),
    'Комментарий должен содержать осмысленный текст',
  )

export const disputeSchema = z.object({
  reason: z.enum([
    'not_published',
    'wrong_time',
    'wrong_text',
    'early_deletion',
    'other',
  ] as const),
  comment: z.string().min(MIN_DISPUTE_COMMENT, `Опишите ситуацию подробнее (мин. ${MIN_DISPUTE_COMMENT} символов)`),
})

export const channelSettingsSchema = z.object({
  price_per_post:      z.number().min(MIN_PRICE_PER_POST, `Минимальная цена ${MIN_PRICE_PER_POST} ₽`),
  max_posts_per_day:   z.number().min(1).max(5),
  max_posts_per_week:  z.number().min(1).max(35),
  publish_start_time:  z.string().regex(/^\d{2}:\d{2}$/, 'Формат: HH:MM'),
  publish_end_time:    z.string().regex(/^\d{2}:\d{2}$/, 'Формат: HH:MM'),
  auto_accept_enabled: z.boolean(),
})

export const counterOfferSchema = z.object({
  price:    z.number().min(MIN_PRICE_PER_POST, `Минимальная цена ${MIN_PRICE_PER_POST} ₽`),
  schedule: z.string().min(1, 'Укажите желаемое время'),
  comment:  z.string().optional(),
})

// ---- Inferred types ----

export type TopUpForm = z.infer<typeof topUpSchema>
export type WithdrawalForm = z.infer<typeof withdrawalSchema>
export type DisputeForm = z.infer<typeof disputeSchema>
export type ChannelSettingsForm = z.infer<typeof channelSettingsSchema>
export type CounterOfferForm = z.infer<typeof counterOfferSchema>
