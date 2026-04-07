import { useState } from 'react'
import { Card, Button, Skeleton, Notification, Select } from '@shared/ui'
import { api } from '@shared/api/client'

interface TaxSummaryData {
  year: number
  quarter: number
  usn_revenue: string
  total_expenses: string
  tax_base_15: string
  calculated_tax_15: string
  min_tax_1: string
  tax_due: string
  applicable_rate: string | null
  vat_accumulated: string
  ndfl_withheld: string
}

function formatRub(value: string): string {
  const num = parseFloat(value)
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

export default function AdminAccounting() {
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.floor((new Date().getMonth() + 3) / 3)

  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)
  const [summaryData, setSummaryData] = useState<TaxSummaryData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSummary = () => {
    setLoading(true)
    setError(null)
    api.get(`admin/tax/summary?year=${year}&quarter=${quarter}`)
      .json<TaxSummaryData>()
      .then((data) => setSummaryData(data))
      .catch((err) => {
        setError(err.message ?? 'Не удалось загрузить налоговую сводку')
        setSummaryData(null)
      })
      .finally(() => setLoading(false))
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">📊 Бухгалтерия</h1>

      {/* Period selector */}
      <Card>
        <div className="flex gap-3 items-end flex-wrap">
          <div>
            <label className="block text-xs text-text-secondary mb-1">Год</label>
            <Select
              value={String(year)}
              onChange={(v) => setYear(Number(v))}
              options={[currentYear - 1, currentYear, currentYear + 1].map((y) => ({ value: String(y), label: String(y) }))}
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

      {error && <Notification type="danger">{error}</Notification>}

      {!summaryData && !loading && !error && (
        <Notification type="info">
          <span className="text-sm">Выберите период и нажмите «Обновить» для загрузки сводки</span>
        </Notification>
      )}

      {summaryData && (
        <>
          {/* Tax summary */}
          <Card title={`📈 Сводка за ${summaryData.year} / Q${summaryData.quarter}`}>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">Доходы</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.usn_revenue)}</p>
              </div>
              <div className="text-center p-3 bg-harbor-elevated rounded-lg">
                <p className="text-xs text-text-secondary">Расходы</p>
                <p className="text-sm font-semibold text-text-primary">{formatRub(summaryData.total_expenses)}</p>
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

          {/* Download */}
          <Card title="📥 Скачать КУДиР">
            <div className="flex gap-3 flex-wrap">
              <Button variant="danger" size="sm" onClick={() => window.open(`/api/admin/tax/kudir/${year}/${quarter}/pdf`, '_blank')}>
                📄 PDF
              </Button>
              <Button variant="success" size="sm" onClick={() => window.open(`/api/admin/tax/kudir/${year}/${quarter}/csv`, '_blank')}>
                📊 CSV
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
