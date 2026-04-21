import type { IconName } from '@shared/ui'
import type { DisputeStatus, DisputeReason } from '@/lib/types/dispute'

export type DisputeTone = 'danger' | 'warning' | 'success' | 'neutral'

export const DISPUTE_STATUS_META: Record<
  DisputeStatus,
  { label: string; tone: DisputeTone; icon: IconName }
> = {
  open: { label: 'Открыт', tone: 'danger', icon: 'warning' },
  owner_explained: { label: 'На рассмотрении', tone: 'warning', icon: 'hourglass' },
  resolved: { label: 'Решён', tone: 'success', icon: 'verified' },
  closed: { label: 'Закрыт', tone: 'neutral', icon: 'archive' },
}

export function getDisputeStatusMeta(status: string) {
  return (
    DISPUTE_STATUS_META[status as DisputeStatus] ?? {
      label: status,
      tone: 'neutral' as DisputeTone,
      icon: 'info' as IconName,
    }
  )
}

export const DISPUTE_TONE_CLASSES: Record<DisputeTone, string> = {
  danger: 'bg-danger-muted text-danger',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

export const DISPUTE_REASON_LABELS: Record<DisputeReason, string> = {
  not_published: 'Не опубликовано',
  wrong_time: 'Нарушение времени',
  wrong_text: 'Изменён текст',
  early_deletion: 'Досрочное удаление',
  post_removed_early: 'Пост удалён досрочно',
  bot_kicked: 'Бот удалён из канала',
  advertiser_complaint: 'Жалоба рекламодателя',
  other: 'Другое',
}

export function getDisputeReasonLabel(reason: string): string {
  return DISPUTE_REASON_LABELS[reason as DisputeReason] ?? reason.replace(/_/g, ' ')
}

export type DisputeRole = 'advertiser' | 'owner' | 'admin'

export function getRoleAwareStatusLabel(
  status: string,
  role: DisputeRole,
): string {
  if (status === 'owner_explained') {
    if (role === 'owner') return 'Вы ответили — ждёт админа'
    if (role === 'advertiser') return 'Владелец ответил — ждёт админа'
    return 'Ожидает решения админа'
  }
  if (status === 'open') {
    if (role === 'owner') return 'Требуется ваш ответ'
    if (role === 'advertiser') return 'Ожидает ответа владельца'
    return 'Открыт'
  }
  return getDisputeStatusMeta(status).label
}
