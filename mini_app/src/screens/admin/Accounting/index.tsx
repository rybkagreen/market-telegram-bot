/**
 * Accounting — Раздел «Бухгалтерия» в Admin Mini App
 *
 * Содержит:
 * - Селектор года/квартала
 * - Карточку налоговой сводки (ООО УСН 15%)
 * - Экспорт КУДиР (PDF/CSV)
 * - Реестр документов
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/client'
import { Notification, Button, Icon, Text } from '@/components/ui'
import AdminLayout from '@/components/admin/AdminLayout'
import TaxSummaryCard from './TaxSummaryCard'
import KudirExportSection from './KudirExportSection'
import DocumentRegistry from './DocumentRegistry'
import * as Sentry from '@sentry/react'
import styles from './accounting.module.css'

interface SummaryData {
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
  kudir_entries: Array<{
    entry_number: number
    operation_date: string
    description: string
    income_amount: string
    expense_amount: string | null
    operation_type: string
  }>
}

export default function Accounting() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.floor((new Date().getMonth() + 3) / 3)

  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)
  const [loading, setLoading] = useState(false)
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchSummary = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api
        .get('admin/tax/summary', { searchParams: { year, quarter } })
        .json<SummaryData>()
      setSummaryData(data)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Не удалось загрузить налоговую сводку'
      setError(msg)
      Sentry.captureException(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AdminLayout>
      <div className={styles.pageContent}>
        <Text variant="xl" weight="bold" font="display">📊 Бухгалтерия</Text>

        {/* Селектор периода + экспорт */}
        <KudirExportSection
          year={year}
          quarter={quarter}
          onYearChange={setYear}
          onQuarterChange={setQuarter}
        />

        {/* Кнопка Обновить */}
        <Button
          variant="primary"
          size="sm"
          loading={loading}
          onClick={fetchSummary}
        >
          <Icon name="RefreshCw" size={16} /> Обновить сводку
        </Button>

        {error && <Notification type="danger">{error}</Notification>}

        {summaryData && <TaxSummaryCard data={summaryData} />}

        <DocumentRegistry />

        {/* Кнопка назад */}
        <div className={styles.backButtonWrap}>
          <Button variant="secondary" fullWidth onClick={() => navigate('/')}>
            <Icon name="House" size={16} /> В главное меню
          </Button>
        </div>
      </div>
    </AdminLayout>
  )
}
