import { useState } from 'react'
import { Card, Button, Skeleton, Notification, Select } from '@shared/ui'
import { useTaxSummary, downloadKudir } from '@/hooks/useAdminQueries'
import type { TaxSummaryData } from '@/api/admin'

export type { KudirEntry, TaxSummaryData } from '@/api/admin'

// eslint-disable-next-line react-refresh/only-export-components
export function formatRub(value: string): string {
  const num = parseFloat(value)
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

interface TaxSummaryBaseProps {
  title: string
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
    if (!enabled) {
      setEnabled(true)
    } else {
      void refetch()
    }
  }

  const displayError = error ?? (queryError ? (queryError as Error).message : null)

  const handleDownload = async (format: 'pdf' | 'csv') => {
    try {
      await downloadKudir(year, quarter, format)
    } catch {
      setError('Ошибка при скачивании файла')
    }
  }

  const incomeClass = coloredKpis ? 'bg-accent-muted' : 'bg-harbor-elevated'
  const expenseClass = coloredKpis ? 'bg-danger-muted' : 'bg-harbor-elevated'
  const incomeTextClass = coloredKpis ? 'text-accent' : 'text-text-primary'
  const expenseTextClass = coloredKpis ? 'text-danger' : 'text-text-primary'

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">{title}</h1>

      {/* Period selector */}
      <Card>
        <div className="flex gap-3 items-end flex-wrap">
          <div>
            <label className="block text-xs text-text-secondary mb-1">Год</label>
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
            <label className="block text-xs text-text-secondary mb-1">Квартал</label>
            <Select
              value={String(quarter)}
              onChange={(v) => setQuarter(Number(v))}
              options={[1, 2, 3, 4].map((q) => ({ value: String(q), label: `Q${q}` }))}
            />
          </div>
          <Button variant="primary" size="sm" loading={loading} onClick={fetchSummary}>
            🔄 Обновить
          </Button>
        </div>
      </Card>

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-24" />
        </div>
      )}

      {displayError && <Notification type="danger">{displayError}</Notification>}

      {showEmptyHint && !summaryData && !loading && !displayError && (
        <Notification type="info">
          <span className="text-sm">Выберите период и нажмите «Обновить» для загрузки сводки</span>
        </Notification>
      )}

      {summaryData && (
        <>
          <Card title={`📈 УСН 15% (доходы − расходы) за ${summaryData.year} / Q${summaryData.quarter}`}>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className={`text-center p-3 ${incomeClass} rounded-lg`}>
                <p className="text-xs text-text-secondary">Доходы</p>
                <p className={`text-sm font-semibold ${incomeTextClass}`}>{formatRub(summaryData.usn_revenue)}</p>
              </div>
              <div className={`text-center p-3 ${expenseClass} rounded-lg`}>
                <p className="text-xs text-text-secondary">Расходы</p>
                <p className={`text-sm font-semibold ${expenseTextClass}`}>{formatRub(summaryData.total_expenses)}</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">Налоговая база</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.tax_base_15)}</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">Налог 15%</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.calculated_tax_15)}</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">Мин. налог 1%</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.min_tax_1)}</p>
              </div>
              <div className="text-center p-3 bg-success-muted rounded-lg">
                <p className="text-xs text-text-secondary">К уплате</p>
                <p className="text-lg font-bold text-success">
                  {formatRub(summaryData.tax_due)}
                  {summaryData.applicable_rate && (
                    <span className="text-xs text-text-tertiary ml-1">({summaryData.applicable_rate})</span>
                  )}
                </p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">НДС накоплено</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.vat_accumulated)}</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">НДФЛ удержано</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.ndfl_withheld)}</p>
              </div>
            </div>
          </Card>

          <Card title="📥 Скачать КУДиР">
            {summaryData.kudir_entries !== undefined && (
              <p className="text-sm text-text-secondary mb-3">
                Книга учёта доходов и расходов за {summaryData.year} / Q{summaryData.quarter}{' '}
                ({summaryData.kudir_entries.length} записей)
              </p>
            )}
            <div className="flex gap-3 flex-wrap">
              <Button variant="danger" size="sm" onClick={() => void handleDownload('pdf')}>
                📄 PDF
              </Button>
              <Button variant="success" size="sm" onClick={() => void handleDownload('csv')}>
                📊 CSV
              </Button>
            </div>
          </Card>

          {children?.(summaryData, year, quarter, (msg) => setError(msg))}
        </>
      )}
    </div>
  )
}
