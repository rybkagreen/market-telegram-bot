import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Skeleton,
  Notification,
  Icon,
  ScreenHeader,
  EmptyState,
} from '@shared/ui'
import { formatDateTimeMSK } from '@/lib/constants'
import { useAdminChannelVerifications } from '@/hooks/useChannelVerificationQueries'
import type { ChannelVerificationStatus } from '@/api/admin_channel_verifications'

type StatusFilter = ChannelVerificationStatus

const FILTERS: { key: StatusFilter; label: string }[] = [
  { key: 'pending_review', label: 'Ожидают' },
  { key: 'verified', label: 'Подтверждены' },
]

export default function AdminChannelVerificationsList() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('pending_review')
  const [page, setPage] = useState(0)
  const limit = 20

  const { data, isLoading, error } = useAdminChannelVerifications({
    status: statusFilter,
    limit,
    offset: page * limit,
  })

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-16" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-[1280px] mx-auto">
        <Notification type="danger">Не удалось загрузить заявки на верификацию.</Notification>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Проверка каналов"
        subtitle={`Реестр блогеров (ФЗ-303) — заявки на ручную верификацию · всего: ${data.total}`}
      />

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => {
            const on = statusFilter === f.key
            return (
              <button
                key={f.key}
                type="button"
                onClick={() => {
                  setStatusFilter(f.key)
                  setPage(0)
                }}
                className={`inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-2xl border transition-all ${
                  on
                    ? 'border-accent bg-accent-muted text-accent'
                    : 'border-border bg-transparent text-text-secondary hover:border-border-active'
                }`}
              >
                {f.label}
              </button>
            )
          })}
        </div>
      </div>

      {data.items.length === 0 ? (
        <EmptyState
          icon="channels"
          title="Заявки не найдены"
          description={
            statusFilter === 'pending_review'
              ? 'Нет ожидающих проверки заявок.'
              : 'Нет подтверждённых каналов с manual_evidence.'
          }
        />
      ) : (
        <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
          {data.items.map((item, i) => {
            const isLast = i === data.items.length - 1
            return (
              <button
                key={item.channel_id}
                type="button"
                onClick={() => navigate(`/admin/channel-verifications/${item.channel_id}`)}
                className={`w-full text-left flex items-center gap-4 px-[18px] py-3.5 hover:bg-harbor-elevated/40 transition-colors ${isLast ? '' : 'border-b border-border'}`}
              >
                <span
                  className="grid place-items-center w-10 h-10 rounded-[10px] flex-shrink-0 bg-accent-muted text-accent"
                  aria-label="Канал на проверке"
                  title="Канал"
                >
                  <Icon name="channels" size={16} />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2.5 flex-wrap">
                    <span className="text-[13.5px] font-semibold text-text-primary truncate max-w-[360px]">
                      {item.channel_title ?? item.channel_username ?? `Канал #${item.channel_id}`}
                    </span>
                    {item.channel_username && (
                      <span className="font-mono text-[11px] text-text-tertiary py-px px-1.5 rounded bg-harbor-elevated">
                        @{item.channel_username}
                      </span>
                    )}
                  </div>
                  <div className="text-[11.5px] text-text-tertiary mt-0.5 flex items-center gap-3 flex-wrap">
                    <span>Владелец #{item.owner_id}{item.owner_username ? ` (@${item.owner_username})` : ''}</span>
                    <span>Подписчиков: {item.member_count.toLocaleString('ru-RU')}</span>
                    <span className="font-mono">№ {item.application_number}</span>
                    <span className="tabular-nums">{formatDateTimeMSK(item.submitted_at)} МСК</span>
                  </div>
                </div>
                <span
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold bg-harbor-elevated text-text-primary border border-border whitespace-nowrap"
                >
                  {item.status === 'verified' ? 'Просмотр' : 'Рассмотреть'}
                  <Icon name="arrow-right" size={12} />
                </span>
              </button>
            )
          })}
        </div>
      )}

      {data.total > limit && (
        <div className="flex items-center justify-between mt-5 py-3.5 px-[18px] rounded-[10px] border border-border bg-harbor-card">
          <Button
            size="sm"
            variant="ghost"
            iconLeft="arrow-left"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Назад
          </Button>
          <div className="flex items-center gap-2.5 text-[12.5px] text-text-secondary">
            <span>Страница</span>
            <span className="font-mono font-semibold text-text-primary py-0.5 px-2.5 rounded-md bg-harbor-elevated border border-border">
              {page + 1}
            </span>
            <span>из {Math.ceil(data.total / limit)}</span>
          </div>
          <Button
            size="sm"
            variant="ghost"
            iconRight="arrow-right"
            disabled={(page + 1) * limit >= data.total}
            onClick={() => setPage(page + 1)}
          >
            Вперёд
          </Button>
        </div>
      )}
    </div>
  )
}
