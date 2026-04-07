import { useState } from 'react'
import { Card, Skeleton, Notification, Button, Select } from '@shared/ui'
import { api } from '@shared/api/client'

interface KudirEntry {
  entry_number: number
  operation_date: string
  description: string
  income_amount: string
  expense_amount: string | null
  operation_type: string
}

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
  total_income: string
  tax_6percent: string
  kudir_entries: KudirEntry[]
}

function formatRub(value: string): string {
  const num = parseFloat(value)
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ₽'
}

export default function AdminTaxSummary() {
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.floor((new Date().getMonth() + 3) / 3)

  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)
  const [loading, setLoading] = useState(false)
  const [summaryData, setSummaryData] = useState<TaxSummaryData | null>(null)
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

  const handleDownload = async (format: 'pdf' | 'csv') => {
    try {
      const endpoint = `/api/admin/tax/kudir/${year}/${quarter}/${format}`
      const response = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${localStorage.getItem('rh_token')}` },
      })
      if (!response.ok) throw new Error('Download failed')
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kudir_${year}_Q${quarter}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError('Ошибка при скачивании файла')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">📊 Налоговая отчётность</h1>

      {/* Quarter selector */}
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

      {loading && <Skeleton className="h-48" />}

      {error && <Notification type="danger">{error}</Notification>}

      {summaryData && (
        <>
          {/* УСН 15% Tax summary */}
          <Card title={`📈 УСН 15% (доходы − расходы) за ${summaryData.year} / Q${summaryData.quarter}`}>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center p-3 bg-accent-muted rounded-lg">
                <p className="text-xs text-text-secondary">Доходы</p>
                <p className="text-sm font-semibold text-accent">{formatRub(summaryData.usn_revenue)}</p>
              </div>
              <div className="text-center p-3 bg-danger-muted rounded-lg">
                <p className="text-xs text-text-secondary">Расходы</p>
                <p className="text-sm font-semibold text-danger">{formatRub(summaryData.total_expenses)}</p>
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

          {/* КУДиР download */}
          <Card title="📥 Экспорт КУДиР">
            <p className="text-sm text-text-secondary mb-3">
              Книга учёта доходов и расходов за {summaryData.year} / Q{summaryData.quarter}
              ({summaryData.kudir_entries.length} записей)
            </p>
            <div className="flex gap-3 flex-wrap">
              <Button variant="danger" size="sm" onClick={() => handleDownload('pdf')}>
                📄 PDF
              </Button>
              <Button variant="success" size="sm" onClick={() => handleDownload('csv')}>
                📊 CSV
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
