import type { PlacementStatus, DisputeStatus, PayoutStatus, ContractStatus, OrdStatus } from '@/lib/types'

interface StatusBadgeProps {
  status: PlacementStatus | DisputeStatus | PayoutStatus | ContractStatus | OrdStatus | string
  className?: string
}

/**
 * StatusBadge — runtime-computed oklch() цвет на основе хеша статуса.
 * style={{}} разрешён для dynamic oklch() значений (исключение из правил).
 */
export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  // Вычисляем hue из строки статуса — даёт стабильный, но уникальный цвет
  const hue = hashCode(status) % 360

  // Tailwind v4 OKLCH формат
  const bgStyle = `oklch(0.65 0.2 ${hue} / 0.12)`
  const textStyle = `oklch(0.72 0.18 ${hue})`
  const borderColorStyle = `oklch(0.72 0.18 ${hue} / 0.3)`

  const label = STATUS_LABELS[status as keyof typeof STATUS_LABELS] ?? status

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${className}`}
      style={{
        backgroundColor: bgStyle,
        color: textStyle,
        borderColor: borderColorStyle,
      }}
    >
      {label}
    </span>
  )
}

function hashCode(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash |= 0
  }
  return Math.abs(hash)
}

const STATUS_LABELS: Record<string, string> = {
  pending_owner: 'Ожидает владельца',
  counter_offer: 'Встречное предложение',
  pending_payment: 'Ожидает оплаты',
  escrow: 'Эскроу',
  published: 'Опубликовано',
  failed: 'Ошибка',
  failed_permissions: 'Нет прав',
  refunded: 'Возврат',
  cancelled: 'Отменено',
  open: 'Открыт',
  owner_reply: 'Ответ владельца',
  resolved: 'Решён',
  closed: 'Закрыт',
  pending: 'Ожидает',
  processing: 'В обработке',
  paid: 'Выплачено',
  rejected: 'Отклонено',
  draft: 'Черновик',
  signed: 'Подписан',
  expired: 'Истёк',
  registered: 'Зарегистрирован',
  token_received: 'Токен получен',
  reported: 'Отправлен в ОРД',
}
