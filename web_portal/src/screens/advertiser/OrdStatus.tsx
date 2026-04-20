import { useParams, useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
  Timeline,
} from '@shared/ui'
import { useOrdStatus, useRegisterOrd } from '@/hooks/useOrdQueries'
import { formatDateTimeMSK } from '@/lib/constants'
import type { OrdStatus as OrdStatusType } from '@/lib/types/billing'

const STATUS_META: Record<OrdStatusType, { label: string; tone: 'info' | 'warning' | 'success' | 'danger'; icon: 'hourglass' | 'pending' | 'verified' | 'check' | 'error' }> = {
  pending: { label: 'Ожидает регистрации', tone: 'warning', icon: 'hourglass' },
  registered: { label: 'Зарегистрировано', tone: 'info', icon: 'pending' },
  token_received: { label: 'Токен получен', tone: 'success', icon: 'verified' },
  reported: { label: 'Отчёт отправлен', tone: 'success', icon: 'check' },
  failed: { label: 'Ошибка', tone: 'danger', icon: 'error' },
}

const toneClasses: Record<'info' | 'warning' | 'success' | 'danger', string> = {
  info: 'bg-info-muted text-info',
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  danger: 'bg-danger-muted text-danger',
}

function buildTimeline(
  current: OrdStatusType,
  createdAt: string | null,
): { id: string; icon: string; title: string; subtitle?: string; variant: 'success' | 'warning' | 'danger' | 'default' }[] {
  const STAGES: Array<{ id: string; key: OrdStatusType; title: string }> = [
    { id: 'pending', key: 'pending', title: 'Создана заявка на ОРД' },
    { id: 'registered', key: 'registered', title: 'Зарегистрировано в ОРД' },
    { id: 'token_received', key: 'token_received', title: 'Получен токен erid' },
    { id: 'reported', key: 'reported', title: 'Отчёт о публикации отправлен' },
  ]
  const order: OrdStatusType[] = ['pending', 'registered', 'token_received', 'reported']
  const idx = order.indexOf(current)

  if (current === 'failed') {
    return STAGES.map((s, i) => ({
      id: s.id,
      icon: '',
      title: s.title,
      subtitle: i === 0 && createdAt ? formatDateTimeMSK(createdAt) : undefined,
      variant: i === 0 ? ('danger' as const) : ('default' as const),
    }))
  }

  return STAGES.map((s, i) => ({
    id: s.id,
    icon: '',
    title: s.title,
    subtitle: i === 0 && createdAt ? formatDateTimeMSK(createdAt) : undefined,
    variant: i < idx ? ('success' as const) : i === idx ? ('warning' as const) : ('default' as const),
  }))
}

export default function OrdStatus() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const numId = id ? parseInt(id, 10) : null
  const { data: ord, isLoading } = useOrdStatus(numId)
  const { mutate: registerOrd, isPending: registering } = useRegisterOrd()

  return (
    <div className="max-w-[900px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Рекламодатель', 'Кампании', `#${id}`, 'Маркировка ОРД']}
        title="Статус маркировки (ОРД)"
        subtitle="Регистрация у оператора рекламных данных (ФЗ-38). Обязательна для публикации рекламы."
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate(-1 as unknown as string)}
          >
            Назад
          </Button>
        }
      />

      <Notification type="info">
        ОРД-маркировка выполняется до публикации поста. После получения erid токен автоматически
        добавляется к рекламному тексту.
      </Notification>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display text-[15px] font-semibold text-text-primary">Ход регистрации</h3>
            {ord && (
              <span
                className={`text-[10.5px] font-bold tracking-[0.08em] uppercase py-1 px-2 rounded ${toneClasses[STATUS_META[ord.status].tone]}`}
              >
                {STATUS_META[ord.status].label}
              </span>
            )}
          </div>

          {isLoading ? (
            <Skeleton className="h-48" />
          ) : !ord ? (
            <div className="text-[13px] text-text-tertiary py-6 text-center">
              Регистрация ещё не начата.
            </div>
          ) : (
            <Timeline events={buildTimeline(ord.status, ord.created_at)} />
          )}
        </div>

        <div className="bg-harbor-card border border-border rounded-xl p-5 h-fit">
          <div className="font-display text-[14px] font-semibold text-text-primary mb-3">Детали</div>
          <dl className="space-y-2.5 text-[13px]">
            <DetailRow icon="verified" label="erid">
              {ord?.erid ? (
                <span className="font-mono text-text-primary break-all">{ord.erid}</span>
              ) : (
                <span className="text-text-tertiary">—</span>
              )}
            </DetailRow>
            <DetailRow icon="docs" label="Провайдер">
              {ord?.ord_provider ?? '—'}
            </DetailRow>
            <DetailRow icon="calendar" label="Создано">
              {ord?.created_at ? formatDateTimeMSK(ord.created_at) : '—'}
            </DetailRow>
          </dl>

          {ord?.error_message && (
            <div className="mt-3">
              <Notification type="danger">{ord.error_message}</Notification>
            </div>
          )}

          {(!ord || ord.status === 'failed') && numId && (
            <div className="mt-4 border-t border-border pt-4">
              <Button
                variant="primary"
                iconLeft="refresh"
                fullWidth
                loading={registering}
                onClick={() => registerOrd(numId)}
              >
                {ord?.status === 'failed' ? 'Повторить регистрацию' : 'Запустить регистрацию'}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function DetailRow({
  icon,
  label,
  children,
}: {
  icon: 'verified' | 'docs' | 'calendar'
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="flex items-center gap-2 text-text-secondary">
        <Icon name={icon} size={13} className="text-text-tertiary" />
        {label}
      </span>
      <span className="text-text-primary text-right">{children}</span>
    </div>
  )
}
