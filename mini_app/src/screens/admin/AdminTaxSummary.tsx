/**
 * AdminTaxSummary — Tax reporting dashboard
 *
 * Features:
 * - Quarter selector (year + quarter)
 * - USN revenue summary table
 * - KUDiR download buttons (PDF/CSV)
 * - Tax calculation (6% USN)
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { Card, Skeleton, Notification, Button, Text, Flex, Icon } from '@/components/ui'
import AdminLayout from '@/components/admin/AdminLayout'
import * as Sentry from '@sentry/react'
import styles from './AdminTaxSummary.module.css'

interface KudirEntry {
  entry_number: number
  operation_date: string
  description: string
  income_amount: string
}

interface TaxSummaryData {
  year: number
  quarter: number
  usn_revenue: string
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
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.floor((new Date().getMonth() + 3) / 3)

  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)
  const [loading, setLoading] = useState(false)
  const [summaryData, setSummaryData] = useState<TaxSummaryData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api
        .get('admin/tax/summary', { searchParams: { year, quarter } })
        .json<TaxSummaryData>()
      setSummaryData(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load tax summary'
      setError(msg)
      Sentry.captureException(err)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (format: 'pdf' | 'csv') => {
    try {
      const endpoint = `admin/tax/kudir/${year}/${quarter}/${format}`
      const response = await api.get(endpoint, { timeout: 30_000 })
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `kudir_${year}_Q${quarter}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      Sentry.captureException(err)
      alert('Ошибка при скачивании файла')
    }
  }

  return (
    <AdminLayout>
      <div className={styles.content}>
        <Text variant="xl" weight="bold" font="display">📊 Налоговая отчётность</Text>

        {/* Quarter Selector */}
        <Card>
          <Flex direction="column" gap={3}>
            <Flex gap={2} align="end" wrap>
              <div>
                <Text variant="xs" color="secondary" as="label">Год</Text>
                <select
                  value={year}
                  onChange={(e) => setYear(Number(e.target.value))}
                  className={styles.select}
                >
                  {[currentYear - 1, currentYear, currentYear + 1].map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>
              <div>
                <Text variant="xs" color="secondary" as="label">Квартал</Text>
                <select
                  value={quarter}
                  onChange={(e) => setQuarter(Number(e.target.value))}
                  className={styles.select}
                >
                  {[1, 2, 3, 4].map((q) => (
                    <option key={q} value={q}>Q{q}</option>
                  ))}
                </select>
              </div>
              <Button
                variant="primary"
                size="sm"
                loading={loading}
                onClick={fetchSummary}
              >
                {loading ? 'Загрузка...' : 'Показать'}
              </Button>
            </Flex>
          </Flex>
        </Card>

        {loading && <Skeleton height={200} radius="md" />}

        {error && <Notification type="danger">{error}</Notification>}

        {summaryData && (
          <>
            {/* Summary Table */}
            <Card title="📈 Сводка за квартал">
              <div className={styles.summaryGrid}>
                <div className={styles.statCell}>
                  <Text variant="xs" color="secondary">Выручка УСН</Text>
                  <Text variant="md" weight="semibold">{formatRub(summaryData.usn_revenue)}</Text>
                </div>
                <div className={styles.statCell}>
                  <Text variant="xs" color="secondary">НДС накоплено</Text>
                  <Text variant="md" weight="semibold">{formatRub(summaryData.vat_accumulated)}</Text>
                </div>
                <div className={styles.statCell}>
                  <Text variant="xs" color="secondary">НДФЛ удержано</Text>
                  <Text variant="md" weight="semibold">{formatRub(summaryData.ndfl_withheld)}</Text>
                </div>
                <div className={styles.statCell}>
                  <Text variant="xs" color="secondary">Налог УСН 6%</Text>
                  <Text variant="md" weight="bold" color="success">{formatRub(summaryData.tax_6percent)}</Text>
                </div>
              </div>
            </Card>

            {/* Download Buttons */}
            <Card title="📥 Скачать КУДиР">
              <Flex gap={2}>
                <Button variant="danger" size="sm" onClick={() => handleDownload('pdf')}>
                  <Icon name="FileText" size={16} /> Скачать PDF
                </Button>
                <Button variant="success" size="sm" onClick={() => handleDownload('csv')}>
                  <Icon name="Sheet" size={16} /> Скачать CSV
                </Button>
              </Flex>
            </Card>

            {/* KUDiR Entries Table */}
            <Card title="📋 Записи КУДиР">
              {summaryData.kudir_entries.length === 0 ? (
                <Text variant="sm" color="muted" align="center">Нет записей за выбранный квартал</Text>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>№</th>
                        <th>Дата</th>
                        <th>Описание</th>
                        <th className={styles.right}>Сумма</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summaryData.kudir_entries.map((entry) => (
                        <tr key={entry.entry_number}>
                          <td>{entry.entry_number}</td>
                          <td>{new Date(entry.operation_date).toLocaleDateString('ru-RU')}</td>
                          <td>{entry.description}</td>
                          <td className={`${styles.right} ${styles.mono}`}>
                            {formatRub(entry.income_amount)}
                          </td>
                        </tr>
                      ))}
                      <tr className={styles.totalRow}>
                        <td colSpan={3}>ИТОГО</td>
                        <td className={`${styles.right} ${styles.mono}`}>
                          {formatRub(summaryData.total_income)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </>
        )}

        {/* Back Button */}
        <div className={styles.backButtonWrap}>
          <Button variant="secondary" fullWidth onClick={() => navigate('/')}>
            <Icon name="House" size={16} /> В главное меню
          </Button>
        </div>
      </div>
    </AdminLayout>
  )
}
