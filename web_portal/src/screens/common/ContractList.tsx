import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { Button, Skeleton, Icon, ScreenHeader, Notification } from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useContracts, usePlatformRules } from '@/hooks/useContractQueries'
import type { Contract, ContractStatus, ContractType } from '@/lib/types/contracts'

const STATUS_META: Record<
  ContractStatus,
  { label: string; pillClass: string; dotClass: string; pulsing: boolean }
> = {
  draft: {
    label: 'Черновик',
    pillClass: 'bg-harbor-elevated text-text-secondary',
    dotClass: 'bg-text-secondary',
    pulsing: false,
  },
  pending: {
    label: 'Ожидает подписи',
    pillClass: 'bg-warning-muted text-warning',
    dotClass: 'bg-warning shadow-[0_0_6px_var(--color-warning)]',
    pulsing: true,
  },
  signed: {
    label: 'Действует',
    pillClass: 'bg-success-muted text-success',
    dotClass: 'bg-success',
    pulsing: false,
  },
  expired: {
    label: 'Истёк',
    pillClass: 'bg-danger-muted text-danger',
    dotClass: 'bg-danger',
    pulsing: false,
  },
  cancelled: {
    label: 'Расторгнут',
    pillClass: 'bg-harbor-elevated text-text-tertiary',
    dotClass: 'bg-text-tertiary',
    pulsing: false,
  },
}

interface ContractKindMeta {
  label: string
  icon: IconName
  tone: 'accent' | 'accent2' | 'warning' | 'success'
}

const KIND_META: Record<ContractType, ContractKindMeta> = {
  owner_service: { label: 'Договор с владельцем', icon: 'channels', tone: 'accent' },
  advertiser_campaign: { label: 'Кампания', icon: 'campaign', tone: 'accent' },
  advertiser_framework: { label: 'Рамочный B2B', icon: 'docs', tone: 'accent' },
  platform_rules: { label: 'Оферта платформы', icon: 'lock', tone: 'accent2' },
  privacy_policy: { label: 'Политика конфиденциальности', icon: 'lock', tone: 'accent2' },
  tax_agreement: { label: 'Налоговое соглашение', icon: 'receipt', tone: 'warning' },
}

const toneIconClass: Record<ContractKindMeta['tone'], string> = {
  accent: 'bg-accent-muted text-accent border-accent/15',
  accent2: 'bg-accent-2-muted text-accent-2 border-accent-2/15',
  warning: 'bg-warning-muted text-warning border-warning/15',
  success: 'bg-success-muted text-success border-success/15',
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'Europe/Moscow',
  })
}

function fmtPeriod(signedAt: string | null, expiresAt: string | null) {
  if (!signedAt) return 'не подписан'
  const left = fmtDate(signedAt)
  const right = expiresAt ? fmtDate(expiresAt) : 'бессрочно'
  return `${left} — ${right}`
}

type KindFilter = 'all' | ContractType

export default function ContractList() {
  const navigate = useNavigate()
  const { data, isLoading } = useContracts()
  const [viewerOpen, setViewerOpen] = useState(false)
  const [kindFilter, setKindFilter] = useState<KindFilter>('all')
  const [q, setQ] = useState('')
  const [activeOnly, setActiveOnly] = useState(false)

  const {
    data: rulesData,
    isLoading: viewerLoading,
    isError: rulesError,
  } = usePlatformRules()

  const viewerHtml = useMemo(() => {
    if (rulesError) return '<p style="color:#e74c3c">Не удалось загрузить текст.</p>'
    if (!rulesData) return ''
    return DOMPurify.sanitize(rulesData.html, {
      ALLOWED_TAGS: ['p', 'strong', 'em', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'br', 'a', 'b', 'i', 'u'],
      ALLOWED_ATTR: ['href', 'class'],
    })
  }, [rulesData, rulesError])

  const items = data?.items ?? []

  const filtered = useMemo(() => {
    return items.filter((c) => {
      if (kindFilter !== 'all' && c.contract_type !== kindFilter) return false
      if (activeOnly && c.contract_status !== 'signed') return false
      if (q) {
        const title = `${KIND_META[c.contract_type]?.label ?? c.contract_type} #${c.id}`
        if (!title.toLowerCase().includes(q.toLowerCase())) return false
      }
      return true
    })
  }, [items, kindFilter, activeOnly, q])

  const metrics = useMemo(() => {
    const signed = items.filter((c) => c.contract_status === 'signed').length
    const pending = items.filter((c) => c.contract_status === 'pending').length
    const total = items.length
    return { signed, pending, total }
  }, [items])

  const KIND_FILTERS: { id: KindFilter; label: string }[] = [
    { id: 'all', label: 'Все' },
    { id: 'owner_service', label: 'Владельцам' },
    { id: 'advertiser_framework', label: 'Рамочные' },
    { id: 'platform_rules', label: 'Оферты' },
    { id: 'tax_agreement', label: 'Налоги' },
  ]

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

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title="Договоры"
        subtitle="Оферты, B2B-договоры с подрядчиками, агентские и налоговые — в одном месте"
        action={
          <Button variant="secondary" size="sm" iconLeft="docs">
            Шаблоны
          </Button>
        }
      />

      <div className="grid gap-3.5 mb-5" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <CLTile icon="lock" tone="success" label="Действующих" value={String(metrics.signed)} sub="договоров" />
        <CLTile icon="clock" tone="warning" label="На подписание" value={String(metrics.pending)} sub="требуют действий" />
        <CLTile icon="docs" tone="accent" label="Всего" value={String(metrics.total)} sub="за всё время" />
        <CLTile icon="receipt" tone="accent2" label="Поиск" value="—" sub="по номеру и контрагенту" />
      </div>

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-3.5 flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-[260px] max-w-[360px] flex items-center gap-2 px-3 py-2 rounded-lg bg-harbor-elevated border border-border">
          <Icon name="search" size={14} className="text-text-tertiary" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск по номеру, контрагенту…"
            className="flex-1 bg-transparent border-0 outline-none text-text-primary text-[13px] placeholder:text-text-tertiary"
          />
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {KIND_FILTERS.map((f) => {
            const on = kindFilter === f.id
            return (
              <button
                key={f.id}
                onClick={() => setKindFilter(f.id)}
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

        <label className="flex items-center gap-2 text-[12.5px] text-text-secondary cursor-pointer">
          <button
            type="button"
            onClick={() => setActiveOnly(!activeOnly)}
            className={`w-[30px] h-[18px] rounded-[10px] border relative transition-colors ${
              activeOnly ? 'bg-accent border-accent' : 'bg-harbor-elevated border-border'
            }`}
          >
            <span
              className={`absolute top-px w-3.5 h-3.5 rounded-full bg-white transition-all ${
                activeOnly ? 'left-[13px]' : 'left-px'
              }`}
            />
          </button>
          Только действующие
        </label>
      </div>

      <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
        <div
          className="hidden md:grid gap-3.5 px-[18px] py-2.5 bg-harbor-secondary border-b border-border text-[10.5px] font-bold uppercase tracking-[0.08em] text-text-tertiary md:[grid-template-columns:1.4fr_2fr_1.2fr_0.9fr_auto]"
        >
          <span>Договор</span>
          <span>Тип</span>
          <span>Период</span>
          <span>Статус</span>
          <span />
        </div>

        {filtered.length === 0 ? (
          <div className="p-[60px] text-center">
            <div className="inline-grid place-items-center w-14 h-14 rounded-[14px] bg-harbor-elevated text-text-tertiary mb-3.5">
              <Icon name="docs" size={22} />
            </div>
            <div className="font-display text-base font-semibold text-text-primary mb-1">
              Ничего не найдено
            </div>
            <div className="text-[13px] text-text-secondary">
              {items.length === 0 ? 'Договоры появятся после начала работы на платформе' : 'Попробуйте изменить фильтры'}
            </div>
          </div>
        ) : (
          filtered.map((c, i) => (
            <ContractRow
              key={c.id}
              c={c}
              isLast={i === filtered.length - 1}
              onClick={() => {
                if (c.contract_type === 'platform_rules' || c.contract_type === 'privacy_policy') {
                  setViewerOpen(true)
                } else {
                  navigate(`/contracts/${c.id}`)
                }
              }}
            />
          ))
        )}
      </div>

      {viewerOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={() => setViewerOpen(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              setViewerOpen(false)
            }
          }}
          tabIndex={0}
          role="button"
          aria-label="Закрыть просмотр правил"
        >
          <div
            className="bg-harbor-card rounded-2xl max-w-2xl w-full max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-border">
              <h3 className="text-lg font-semibold text-text-primary">
                Правила и Политика конфиденциальности
              </h3>
              <button
                className="text-text-tertiary hover:text-text-primary"
                onClick={() => setViewerOpen(false)}
              >
                ✕
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 prose prose-invert max-w-none">
              {viewerLoading ? (
                <Notification type="info">Загрузка…</Notification>
              ) : (
                <div dangerouslySetInnerHTML={{ __html: viewerHtml }} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const tileIconBg: Record<'accent' | 'accent2' | 'success' | 'warning', string> = {
  accent: 'bg-accent-muted text-accent',
  accent2: 'bg-accent-2-muted text-accent-2',
  success: 'bg-success-muted text-success',
  warning: 'bg-warning-muted text-warning',
}

function CLTile({
  icon,
  tone,
  label,
  value,
  sub,
}: {
  icon: IconName
  tone: 'accent' | 'accent2' | 'success' | 'warning'
  label: string
  value: string
  sub: string
}) {
  return (
    <div className="bg-harbor-card border border-border rounded-xl p-4 flex gap-3 items-start">
      <span className={`grid place-items-center w-[38px] h-[38px] rounded-[9px] flex-shrink-0 ${tileIconBg[tone]}`}>
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

function ContractRow({
  c,
  isLast,
  onClick,
}: {
  c: Contract
  isLast: boolean
  onClick: () => void
}) {
  const st = STATUS_META[c.contract_status]
  const km = KIND_META[c.contract_type] ?? { label: c.contract_type, icon: 'docs' as IconName, tone: 'accent' as const }
  const period = fmtPeriod(c.signed_at, c.expires_at)

  return (
    <div
      className={`px-4 md:px-[18px] py-3.5 transition-colors hover:bg-harbor-elevated/40 ${
        isLast ? '' : 'border-b border-border'
      } flex flex-col gap-3 md:grid md:gap-3.5 md:items-center md:[grid-template-columns:1.4fr_2fr_1.2fr_0.9fr_auto]`}
    >
      {/* ── Mobile: single stacked card.  Desktop: Col 1 (icon + #id + version) ── */}
      <div className="flex items-center gap-3 min-w-0">
        <span
          className={`w-10 h-10 md:w-9 md:h-9 rounded-[9px] grid place-items-center border flex-shrink-0 ${toneIconClass[km.tone]}`}
          aria-label={st.label}
          title={st.label}
        >
          <Icon name={km.icon} size={16} />
        </span>
        <div className="flex-1 min-w-0">
          {/* Mobile header: #id + type on one line; Desktop: #id stands alone */}
          <div className="flex items-baseline gap-2 flex-wrap md:flex-nowrap">
            <span className="font-mono text-[13px] md:text-[12.5px] font-semibold text-text-primary">
              #{c.id}
            </span>
            <span className="text-[13px] font-medium text-text-primary md:hidden truncate">
              {km.label}
            </span>
          </div>
          <div className="text-[11px] text-text-tertiary mt-0.5 font-semibold tracking-wider uppercase">
            v{c.template_version}
          </div>
        </div>
        {/* Mobile status dot — moved to the right of the row header */}
        <span
          className={`md:hidden inline-grid place-items-center w-6 h-6 rounded-full flex-shrink-0 ${st.pillClass}`}
          aria-label={st.label}
          title={st.label}
        >
          <span className={`w-2 h-2 rounded-full ${st.dotClass}`} />
        </span>
      </div>

      {/* Desktop Col 2 — type label (hidden on mobile, shown above) */}
      <div className="hidden md:block min-w-0">
        <div className="text-[13px] font-medium text-text-primary truncate">{km.label}</div>
        {c.kep_requested && (
          <div className="text-[11px] text-warning mt-0.5">КЭП запрошена</div>
        )}
      </div>

      {/* Period: unified single string on mobile and desktop */}
      <div className="text-xs text-text-secondary tabular-nums min-w-0">
        <span className="md:hidden text-[11px] uppercase tracking-wider text-text-tertiary mr-1.5">
          Период:
        </span>
        {period}
        {c.kep_requested && (
          <span className="md:hidden ml-2 text-[11px] text-warning font-semibold">КЭП</span>
        )}
      </div>

      {/* Desktop status pill — text visible only on desktop; mobile uses dot above */}
      <span
        className={`hidden md:inline-grid place-items-center w-7 h-7 rounded-full ${st.pillClass} justify-self-start`}
        aria-label={st.label}
        title={st.label}
      >
        <span className={`w-2 h-2 rounded-full ${st.dotClass}`} />
      </span>

      {/* Actions — full-width buttons on mobile, compact on desktop */}
      <div className="flex gap-2 justify-end md:gap-1">
        {c.contract_status === 'pending' && (
          <Button size="sm" variant="primary" iconLeft="check" onClick={onClick}>
            Подписать
          </Button>
        )}
        {c.contract_status !== 'pending' && (
          <Button size="sm" variant="secondary" onClick={onClick}>
            Открыть
          </Button>
        )}
        {c.pdf_url && (
          <button
            title="PDF"
            aria-label="Скачать PDF"
            onClick={(e) => {
              e.stopPropagation()
              window.open(c.pdf_url!, '_blank')
            }}
            className="w-11 h-11 md:w-[30px] md:h-[30px] rounded-md border border-border bg-harbor-elevated text-text-secondary grid place-items-center hover:text-text-primary transition-colors flex-shrink-0"
          >
            <Icon name="download" size={14} />
          </button>
        )}
      </div>
    </div>
  )
}
