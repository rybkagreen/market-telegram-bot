import type { IconName } from '@shared/ui/icon-names'

export type PlacementStatus =
  | 'pending_owner'
  | 'counter_offer'
  | 'pending_payment'
  | 'escrow'
  | 'published'
  | 'cancelled'
  | 'refunded'
  | 'failed'
  | 'failed_permissions'

export type StatusTone =
  | 'info'
  | 'warning'
  | 'success'
  | 'neutral'
  | 'danger'
  | 'accent2'

export type PlacementRole = 'advertiser' | 'owner'

export interface PlacementStatusMeta {
  label: string
  tone: StatusTone
  icon: IconName
}

const BASE: Record<PlacementStatus, { tone: StatusTone; icon: IconName }> = {
  pending_owner: { tone: 'warning', icon: 'hourglass' },
  counter_offer: { tone: 'accent2', icon: 'refresh' },
  pending_payment: { tone: 'warning', icon: 'card' },
  escrow: { tone: 'info', icon: 'lock' },
  published: { tone: 'success', icon: 'check' },
  cancelled: { tone: 'neutral', icon: 'close' },
  refunded: { tone: 'neutral', icon: 'refund' },
  failed: { tone: 'danger', icon: 'error' },
  failed_permissions: { tone: 'danger', icon: 'blocked' },
}

const LABELS: Record<PlacementRole, Record<PlacementStatus, string>> = {
  advertiser: {
    pending_owner: 'Ожидает владельца',
    counter_offer: 'Контр-оферта',
    pending_payment: 'Ожидает оплаты',
    escrow: 'В эскроу',
    published: 'Опубликован',
    cancelled: 'Отменён',
    refunded: 'Возврат',
    failed: 'Ошибка',
    failed_permissions: 'Нет прав',
  },
  owner: {
    pending_owner: 'Новая',
    counter_offer: 'Контр-оферта',
    pending_payment: 'Ожидает оплаты',
    escrow: 'В эскроу',
    published: 'Опубликован',
    cancelled: 'Отменён',
    refunded: 'Возврат',
    failed: 'Ошибка',
    failed_permissions: 'Нет прав',
  },
}

export function getPlacementStatusMeta(
  status: string,
  role: PlacementRole,
): PlacementStatusMeta {
  const key = status as PlacementStatus
  const base = BASE[key]
  if (!base) {
    return { label: status, tone: 'neutral', icon: 'info' }
  }
  return { label: LABELS[role][key], tone: base.tone, icon: base.icon }
}

export const statusToneClasses: Record<StatusTone, string> = {
  info: 'bg-info-muted text-info',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
  danger: 'bg-danger-muted text-danger',
  accent2: 'bg-accent-2-muted text-accent-2',
}

export const ACTIVE_STATUSES: PlacementStatus[] = [
  'pending_owner',
  'counter_offer',
  'pending_payment',
  'escrow',
]
export const COMPLETED_STATUSES: PlacementStatus[] = ['published']
export const CANCELLED_STATUSES: PlacementStatus[] = [
  'cancelled',
  'refunded',
  'failed',
  'failed_permissions',
]
