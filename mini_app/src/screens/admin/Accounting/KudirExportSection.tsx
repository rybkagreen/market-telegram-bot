/**
 * KudirExportSection — Селектор периода и кнопки экспорта КУДиР
 */

import { useState } from 'react'
import { api } from '@/api/client'
import { Button, Icon, Text, Flex } from '@/components/ui'
import * as Sentry from '@sentry/react'
import styles from './accounting.module.css'

interface Props {
  year: number
  quarter: number
  onYearChange: (y: number) => void
  onQuarterChange: (q: number) => void
}

export default function KudirExportSection({ year, quarter, onYearChange, onQuarterChange }: Props) {
  const [downloading, setDownloading] = useState<string | null>(null)

  const handleDownload = async (format: 'pdf' | 'csv') => {
    setDownloading(format)
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
    } finally {
      setDownloading(null)
    }
  }

  const currentYear = new Date().getFullYear()

  return (
    <div className={styles.card}>
      <Text variant="lg" weight="semibold" font="display" className={styles.cardTitle}>
        📥 Экспорт КУДиР
      </Text>

      {/* Селектор периода */}
      <Flex gap={2} align="end" wrap>
        <div>
          <Text variant="xs" color="secondary" as="label">Год</Text>
          <select
            value={year}
            onChange={(e) => onYearChange(Number(e.target.value))}
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
            onChange={(e) => onQuarterChange(Number(e.target.value))}
            className={styles.select}
          >
            {[1, 2, 3, 4].map((q) => (
              <option key={q} value={q}>Q{q}</option>
            ))}
          </select>
        </div>
      </Flex>

      {/* Кнопки экспорта */}
      <div className={styles.exportButtonsWrap}>
        <Flex gap={2}>
          <Button
            variant="danger"
            size="sm"
            fullWidth
            loading={downloading === 'pdf'}
            onClick={() => handleDownload('pdf')}
          >
            <Icon name="FileText" size={16} /> Скачать КУДиР (PDF)
          </Button>
          <Button
            variant="success"
            size="sm"
            fullWidth
            loading={downloading === 'csv'}
            onClick={() => handleDownload('csv')}
          >
            <Icon name="Sheet" size={16} /> Скачать КУДиР (CSV)
          </Button>
        </Flex>
      </div>
    </div>
  )
}
