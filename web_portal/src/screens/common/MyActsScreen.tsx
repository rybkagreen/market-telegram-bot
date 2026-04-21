import { useMemo, useState } from 'react'
import { Button, Skeleton, Notification, Icon, ScreenHeader } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useMyActs, useSignAct, downloadActPdf } from '@/hooks/useActQueries'
import type { Act } from '@/api/acts'

type ActType = 'income' | 'expense'
type TypeFilter = 'all' | ActType
type StatusFilter = 'all' | 'pending' | 'draft' | 'signed'

const TYPE_META: Record<ActType, { label: string; full: string; icon: IconName; tone: 'accent' | 'accent2' }> = {
  income: { label: 'Акт-ИСХ', full: 'Исходящий', icon: 'payouts', tone: 'accent' },
  expense: { label: 'Акт-ВХ', full: 'Входящий', icon: 'topup', tone: 'accent2' },
}

const STATUS_META: Record<
  Act['sign_status'],
  { label: string; pillClass: string; dotClass: string; pulsing: boolean }
> = {
  draft: {
    label: 'Черновик',
    pillClass: 'bg-harbor-elevated text-text-tertiary',
    dotClass: 'bg-text-tertiary',
    pulsing: false,
  },
  pending: {
    label: 'Ожидает',
    pillClass: 'bg-warning-muted text-warning',
    dotClass: 'bg-warning shadow-[0_0_6px_var(--color-warning)]',
    pulsing: true,
  },
  signed: {
    label: 'Подписан',
    pillClass: 'bg-success-muted text-success',
    dotClass: 'bg-success',
    pulsing: false,
  },
  auto_signed: {
    label: 'Авто-подписан',
    pillClass: 'bg-success-muted text-success',
    dotClass: 'bg-success',
    pulsing: false,
  },
}

const TYPE_FILTERS: { id: TypeFilter; label: string }[] = [
  { id: 'all', label: 'Все' },
  { id: 'income', label: 'Исходящие' },
  { id: 'expense', label: 'Входящие' },
]

const STATUS_FILTERS: { id: StatusFilter; label: string }[] = [
  { id: 'all', label: 'Все статусы' },
  { id: 'pending', label: 'Ожидают' },
  { id: 'draft', label: 'Черновики' },
  { id: 'signed', label: 'Подписанные' },
]

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    timeZone: 'Europe/Moscow',
  })
}

function actType(a: Act): ActType {
  return a.act_type === 'expense' ? 'expense' : 'income'
}

export default function MyActsScreen() {
  const { data, isLoading, isError, refetch } = useMyActs({ limit: 50 })
  const signMutation = useSignAct()
  const [error, setError] = useState<string | null>(null)
  const [downloadingId, setDownloadingId] = useState<number | null>(null)
  const [typeF, setTypeF] = useState<TypeFilter>('all')
  const [statusF, setStatusF] = useState<StatusFilter>('all')
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const acts = data?.items ?? []

  const filtered = useMemo(() => {
    return acts.filter((a) => {
      if (typeF !== 'all' && actType(a) !== typeF) return false
      if (statusF === 'signed' && !(a.sign_status === 'signed' || a.sign_status === 'auto_signed')) return false
      if (statusF === 'pending' && a.sign_status !== 'pending') return false
      if (statusF === 'draft' && a.sign_status !== 'draft') return false
      return true
    })
  }, [acts, typeF, statusF])

  const pendingAll = acts.filter((a) => a.sign_status === 'pending')
  const signedCount = acts.filter((a) => a.sign_status === 'signed' || a.sign_status === 'auto_signed').length
  const outgoingSigned = acts.filter(
    (a) => actType(a) === 'income' && (a.sign_status === 'signed' || a.sign_status === 'auto_signed'),
  ).length
  const incomingSigned = acts.filter(
    (a) => actType(a) === 'expense' && (a.sign_status === 'signed' || a.sign_status === 'auto_signed'),
  ).length
  const pendingOrDraft = acts.filter((a) => a.sign_status === 'pending' || a.sign_status === 'draft').length

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSign = (actId: number) => {
    signMutation.mutate(actId, {
      onError: () => setError('Ошибка при подписании акта'),
    })
  }

  const handleDownload = async (actId: number) => {
    setDownloadingId(actId)
    try {
      await downloadActPdf(actId)
    } catch {
      setError('Ошибка при скачивании PDF')
    } finally {
      setDownloadingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Skeleton className="h-14" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
        <Skeleton className="h-16" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="max-w-[1280px] mx-auto space-y-4">
        <Notification type="danger">{error ?? 'Не удалось загрузить акты'}</Notification>
        <Button variant="secondary" fullWidth onClick={() => refetch()}>
          Повторить
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Мои акты"
        subtitle="Первичные документы по каждому размещению и выплате — подписывайте онлайн или скачивайте PDF"
        action={
          <>
            <Button
              variant="ghost"
              size="sm"
              icon
              onClick={() => refetch()}
              title="Синхронизировать"
              aria-label="Синхронизировать"
            >
              <Icon name="refresh" size={14} />
            </Button>
            <Button variant="secondary" size="sm" iconLeft="download">
              Скачать ZIP
            </Button>
          </>
        }
      />

      {error && (
        <div className="mb-5">
          <Notification type="danger">{error}</Notification>
        </div>
      )}

      {pendingAll.length > 0 && (
        <div className="bg-gradient-to-br from-warning-muted to-warning-muted/40 border border-warning/35 border-l-[3px] border-l-warning rounded-[10px] py-3.5 px-[18px] mb-5 flex items-center gap-4">
          <span className="grid place-items-center w-10 h-10 rounded-[10px] bg-warning/15 text-warning flex-shrink-0">
            <Icon name="warning" size={18} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="font-display text-sm font-semibold text-text-primary">
              {pendingAll.length} акт{pendingAll.length === 1 ? '' : pendingAll.length < 5 ? 'а' : 'ов'} ожида
              {pendingAll.length === 1 ? 'ет' : 'ют'} подписания
            </div>
            <div className="text-[12.5px] text-text-secondary mt-0.5">
              Подпишите в срок, иначе они будут подписаны автоматически
            </div>
          </div>
          <Button variant="primary" size="sm">
            Подписать все
          </Button>
        </div>
      )}

      <div className="grid gap-3.5 mb-5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <ActTile icon="clock" tone="warning" label="Ожидают подписания" value={String(pendingOrDraft)} sub="действий требуется" />
        <ActTile icon="check" tone="success" label="Подписанные" value={String(signedCount)} sub="всего" />
        <ActTile icon="payouts" tone="accent" label="Исходящие" value={String(outgoingSigned)} sub="по подписанным" />
        <ActTile icon="topup" tone="accent2" label="Входящие" value={String(incomingSigned)} sub="по подписанным" />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3.5 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-tertiary font-medium">Тип:</span>
          <div className="flex p-[3px] rounded-lg bg-harbor-elevated border border-border">
            {TYPE_FILTERS.map((f) => {
              const on = typeF === f.id
              return (
                <button
                  key={f.id}
                  onClick={() => setTypeF(f.id)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-[5px] transition-colors ${
                    on ? 'bg-harbor-card text-text-primary' : 'text-text-secondary'
                  }`}
                >
                  {f.label}
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-wrap">
          {STATUS_FILTERS.map((f) => {
            const on = statusF === f.id
            return (
              <button
                key={f.id}
                onClick={() => setStatusF(f.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-2xl border transition-all ${
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

        <div className="flex-1" />

        {selected.size > 0 ? (
          <div className="flex items-center gap-2.5">
            <span className="text-[12.5px] text-text-secondary">
              Выбрано: <span className="text-text-primary font-semibold">{selected.size}</span>
            </span>
            <Button size="sm" variant="secondary" iconLeft="download">
              Скачать
            </Button>
            <Button size="sm" variant="primary" iconLeft="check">
              Подписать
            </Button>
          </div>
        ) : (
          <span className="text-xs text-text-tertiary font-mono tabular-nums">
            {filtered.length} актов
          </span>
        )}
      </div>

      <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
        <div
          className="grid gap-3.5 px-[18px] py-2.5 bg-harbor-secondary border-b border-border text-[10.5px] font-bold uppercase tracking-[0.08em] text-text-tertiary"
          style={{ gridTemplateColumns: '40px 1.2fr 1.8fr 0.9fr 0.9fr auto' }}
        >
          <span />
          <span>Акт</span>
          <span>Основание</span>
          <span>Дата</span>
          <span className="text-right">Заявка</span>
          <span>Статус · Действия</span>
        </div>

        {filtered.length === 0 ? (
          <div className="p-[60px] text-center">
            <div className="inline-grid place-items-center w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary mb-3.5">
              <Icon name="docs" size={22} />
            </div>
            <div className="font-display text-base font-semibold text-text-primary mb-1">
              Актов пока нет
            </div>
            <div className="text-[13px] text-text-secondary">
              Акты появятся после завершения размещений
            </div>
          </div>
        ) : (
          filtered.map((act, i) => (
            <ActRow
              key={act.id}
              act={act}
              selected={selected.has(act.id)}
              onToggle={() => toggle(act.id)}
              isLast={i === filtered.length - 1}
              signing={signMutation.isPending && signMutation.variables === act.id}
              downloading={downloadingId === act.id}
              onSign={() => handleSign(act.id)}
              onDownload={() => handleDownload(act.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

const toneIconBg: Record<'warning' | 'success' | 'accent' | 'accent2', string> = {
  warning: 'bg-warning-muted text-warning',
  success: 'bg-success-muted text-success',
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
}

function ActTile({
  icon,
  tone,
  label,
  value,
  sub,
}: {
  icon: IconName
  tone: 'warning' | 'success' | 'accent' | 'accent2'
  label: string
  value: string
  sub: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-4 flex gap-3 items-start">
      <span
        className={`grid place-items-center w-[38px] h-[38px] rounded-[9px] flex-shrink-0 ${toneIconBg[tone]}`}
      >
        <Icon name={icon} size={16} />
      </span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-text-tertiary mb-1">
          {label}
        </div>
        <div className="font-display text-xl font-bold text-text-primary tracking-[-0.02em] tabular-nums truncate">
          {value}
        </div>
        <div className="text-[11.5px] text-text-tertiary mt-0.5">{sub}</div>
      </div>
    </div>
  )
}

const typeIconClass: Record<'accent' | 'accent2', string> = {
  accent: 'bg-accent-muted text-accent border-accent/15',
  accent2: 'bg-accent-2-muted text-accent-2 border-accent-2/15',
}

function ActRow({
  act,
  selected,
  onToggle,
  isLast,
  signing,
  downloading,
  onSign,
  onDownload,
}: {
  act: Act
  selected: boolean
  onToggle: () => void
  isLast: boolean
  signing: boolean
  downloading: boolean
  onSign: () => void
  onDownload: () => void
}) {
  const t = actType(act)
  const tm = TYPE_META[t]
  const sm = STATUS_META[act.sign_status]
  const canSign = act.sign_status === 'draft' || act.sign_status === 'pending'

  return (
    <div
      className={`grid gap-3.5 px-[18px] py-3.5 items-center transition-colors ${
        selected ? 'bg-accent-muted/40' : 'hover:bg-harbor-elevated/40'
      } ${isLast ? '' : 'border-b border-border'}`}
      style={{ gridTemplateColumns: '40px 1.2fr 1.8fr 0.9fr 0.9fr auto' }}
    >
      <button
        onClick={onToggle}
        className={`w-5 h-5 rounded-[5px] grid place-items-center border-[1.5px] p-0 text-white justify-self-start transition-colors ${
          selected ? 'bg-accent border-accent' : 'bg-harbor-elevated border-border'
        }`}
      >
        {selected && <Icon name="check" size={12} strokeWidth={2.5} />}
      </button>

      <div className="flex items-center gap-[11px] min-w-0">
        <span
          className={`w-9 h-9 rounded-[9px] grid place-items-center border flex-shrink-0 ${typeIconClass[tm.tone]}`}
        >
          <Icon name={tm.icon} size={16} />
        </span>
        <div className="min-w-0">
          <div className="font-mono text-[13px] font-semibold text-text-primary tracking-[-0.005em]">
            № {act.act_number ?? act.id}
          </div>
          <div className="text-[11.5px] text-text-tertiary mt-0.5">{tm.full} акт</div>
        </div>
      </div>

      <div className="min-w-0">
        <div className="text-[13px] font-medium text-text-primary truncate">
          {tm.full === 'Входящий' ? 'Размещение' : 'Выплата'} #{act.placement_request_id}
        </div>
        {act.placement_request_id && (
          <div className="text-[11px] text-text-tertiary mt-0.5 flex items-center gap-1.5">
            <Icon name="placement" size={11} />
            <span className="font-mono">Заявка #{act.placement_request_id}</span>
          </div>
        )}
      </div>

      <div className="text-[12.5px] text-text-secondary tabular-nums">{fmtDate(act.act_date)}</div>

      <div className="font-mono tabular-nums text-sm font-semibold text-text-primary text-right">
        #{act.placement_request_id}
      </div>

      <div className="flex items-center gap-2.5 justify-end">
        <span
          className={`inline-flex items-center gap-1.5 text-[11px] font-bold tracking-wider uppercase py-1 px-2.5 rounded-[5px] whitespace-nowrap ${sm.pillClass}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${sm.dotClass}`} />
          {sm.label}
        </span>

        <div className="flex gap-1">
          {canSign && (
            <Button
              size="sm"
              variant="primary"
              iconLeft="check"
              loading={signing}
              onClick={onSign}
            >
              Подписать
            </Button>
          )}
          {act.pdf_url && (
            <button
              title="Скачать PDF"
              onClick={onDownload}
              disabled={downloading}
              className="w-[30px] h-[30px] rounded-md border border-border bg-harbor-elevated text-text-secondary grid place-items-center hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Icon name="download" size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
