import { useState } from 'react'
import {
  Button,
  Skeleton,
  Notification,
  Select,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import type { IconName } from '@shared/ui'
import { useTaxSummary, downloadKudir } from '@/hooks/useAdminQueries'
import type { TaxSummaryData } from '@/api/admin'

export type { KudirEntry, TaxSummaryData } from '@/api/admin'

// eslint-disable-next-line react-refresh/only-export-components
export function formatRub(value: string): string {
  const num = parseFloat(value)
  return (
    num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
  )
}

interface TaxSummaryBaseProps {
  title: string
  subtitle?: string
  /** Use colored accent/danger KPI cards instead of neutral harbor-elevated */
  coloredKpis?: boolean
  /** Show empty state hint before first load */
  showEmptyHint?: boolean
  /** Kept for backward compatibility — always fetches with Bearer auth */
  downloadMode?: 'auth'
  /** Extra content rendered below the KPI grid, receives current data + helpers */
  children?: (
    data: TaxSummaryData,
    year: number,
    quarter: number,
    setError: (msg: string) => void,
  ) => React.ReactNode
}

export default function TaxSummaryBase({
  title,
  subtitle,
  coloredKpis = false,
  showEmptyHint = false,
  children,
}: TaxSummaryBaseProps) {
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.floor((new Date().getMonth() + 3) / 3)

  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)
  const [enabled, setEnabled] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    data: summaryData,
    isFetching: loading,
    error: queryError,
    refetch,
  } = useTaxSummary(year, quarter, enabled)

  const fetchSummary = () => {
    setError(null)
    if (!enabled) setEnabled(true)
    else void refetch()
  }

  const displayError = error ?? (queryError ? (queryError as Error).message : null)

  const handleDownload = async (format: 'pdf' | 'csv') => {
    try {
      await downloadKudir(year, quarter, format)
    } catch {
      setError('Ошибка при скачивании файла')
    }
  }

  return (
    <div className="max-w-[1280px] mx-auto">
      <ScreenHeader
        title={title}
        subtitle={subtitle ?? 'Выберите период и обновите сводку — появятся КУДиР и налоговые показатели.'}
      />

      <div className="bg-harbor-card border border-border rounded-xl p-3.5 mb-4 flex gap-3 items-end flex-wrap">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-text-tertiary mb-1">Год</div>
          <Select
            value={String(year)}
            onChange={(v) => setYear(Number(v))}
            options={[currentYear - 1, currentYear, currentYear + 1].map((y) => ({
              value: String(y),
              label: String(y),
            }))}
          />
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wider text-text-tertiary mb-1">Квартал</div>
          <Select
            value={String(quarter)}
            onChange={(v) => setQuarter(Number(v))}
            options={[1, 2, 3, 4].map((q) => ({ value: String(q), label: `Q${q}` }))}
          />
        </div>
        <Button variant="primary" iconLeft="refresh" loading={loading} onClick={fetchSummary}>
          Обновить сводку
        </Button>
      </div>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-24" />
        </div>
      )}

      {displayError && <Notification type="danger">{displayError}</Notification>}

      {showEmptyHint && !summaryData && !loading && !displayError && (
        <Notification type="info">
          Выберите период и нажмите «Обновить сводку», чтобы загрузить данные.
        </Notification>
      )}

      {summaryData && (
        <>
          <div className="bg-harbor-card border border-border rounded-xl overflow-hidden mb-4">
            <div className="px-5 py-3 border-b border-border flex items-center gap-2">
              <Icon name="tax-doc" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                УСН 15% (доходы − расходы) за {summaryData.year} / Q{summaryData.quarter}
              </span>
            </div>
            <div
              className="grid gap-2.5 p-4"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}
            >
              <KpiCell
                icon="arrow-down"
                label="Доходы"
                value={formatRub(summaryData.usn_revenue)}
                tone={coloredKpis ? 'accent' : 'neutral'}
              />
              <KpiCell
                icon="arrow-up"
                label="Расходы"
                value={formatRub(summaryData.total_expenses)}
                tone={coloredKpis ? 'danger' : 'neutral'}
              />
              <KpiCell
                icon="percent"
                label="Налоговая база"
                value={formatRub(summaryData.tax_base_15)}
                tone="neutral"
              />
              <KpiCell
                icon="tax-doc"
                label="Налог 15%"
                value={formatRub(summaryData.calculated_tax_15)}
                tone="neutral"
              />
              <KpiCell
                icon="info"
                label="Мин. налог 1%"
                value={formatRub(summaryData.min_tax_1)}
                tone="neutral"
              />
              <KpiCell
                icon="check"
                label={`К уплате${summaryData.applicable_rate ? ` (${summaryData.applicable_rate})` : ''}`}
                value={formatRub(summaryData.tax_due)}
                tone="success"
                emphasize
              />
              <KpiCell
                icon="receipt"
                label="НДС накоплено"
                value={formatRub(summaryData.vat_accumulated)}
                tone="neutral"
              />
              <KpiCell
                icon="withdraw"
                label="НДФЛ удержано"
                value={formatRub(summaryData.ndfl_withheld)}
                tone="neutral"
              />
            </div>
          </div>

          <div className="bg-harbor-card border border-border rounded-xl p-5 mb-4">
            <div className="flex items-center gap-2 mb-3">
              <Icon name="download" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Скачать КУДиР
              </span>
            </div>
            {summaryData.kudir_entries !== undefined && (
              <p className="text-[13px] text-text-secondary mb-3">
                Книга учёта доходов и расходов за {summaryData.year} / Q{summaryData.quarter} ·{' '}
                {summaryData.kudir_entries.length} записей
              </p>
            )}
            <div className="flex gap-2 flex-wrap">
              <Button variant="secondary" iconLeft="docs" onClick={() => void handleDownload('pdf')}>
                Скачать PDF
              </Button>
              <Button variant="secondary" iconLeft="export" onClick={() => void handleDownload('csv')}>
                Скачать CSV
              </Button>
            </div>
          </div>

          {children?.(summaryData, year, quarter, (msg) => setError(msg))}
        </>
      )}
    </div>
  )
}

const toneClass: Record<'accent' | 'danger' | 'success' | 'neutral', string> = {
  accent: 'bg-accent-muted text-accent',
  danger: 'bg-danger-muted text-danger',
  success: 'bg-success-muted text-success',
  neutral: 'bg-harbor-elevated text-text-tertiary',
}

function KpiCell({
  icon,
  label,
  value,
  tone,
  emphasize,
}: {
  icon: IconName
  label: string
  value: string
  tone: 'accent' | 'danger' | 'success' | 'neutral'
  emphasize?: boolean
}) {
  return (
    <div className="bg-harbor-secondary border border-border rounded-[10px] p-3 flex gap-2.5 items-center">
      <span className={`grid place-items-center w-8 h-8 rounded-md flex-shrink-0 ${toneClass[tone]}`}>
        <Icon name={icon} size={13} />
      </span>
      <div className="min-w-0">
        <div className="text-[10.5px] uppercase tracking-wider text-text-tertiary truncate">
          {label}
        </div>
        <div
          className={`font-mono tabular-nums font-semibold truncate ${emphasize ? 'text-success text-[15px]' : 'text-text-primary text-[13.5px]'}`}
        >
          {value}
        </div>
      </div>
    </div>
  )
}
