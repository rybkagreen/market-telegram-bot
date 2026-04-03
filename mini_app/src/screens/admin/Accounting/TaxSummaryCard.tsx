/**
 * TaxSummaryCard — Карточка налоговой сводки (ООО УСН 15%)
 *
 * Отображает: доходы, расходы, налоговую базу, рассчитанный налог,
 * минимальный налог 1%, к уплате и применимую ставку.
 */

import { Text, Flex } from '@/components/ui'
import styles from './accounting.module.css'

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

interface Props {
  data: TaxSummaryData
}

export default function TaxSummaryCard({ data }: Props) {
  return (
    <div className={styles.card}>
      <Text variant="lg" weight="semibold" font="display" className={styles.cardTitle}>
        📈 Сводка за {data.year} / Q{data.quarter}
      </Text>

      <div className={styles.summaryGrid}>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">Доходы</Text>
          <Text variant="md" weight="semibold">{formatRub(data.usn_revenue)}</Text>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">Расходы</Text>
          <Text variant="md" weight="semibold">{formatRub(data.total_expenses)}</Text>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">Налоговая база</Text>
          <Text variant="md" weight="semibold">{formatRub(data.tax_base_15)}</Text>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">Налог 15%</Text>
          <Text variant="md" weight="semibold">{formatRub(data.calculated_tax_15)}</Text>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">Мин. налог 1%</Text>
          <Text variant="md" weight="semibold">{formatRub(data.min_tax_1)}</Text>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">К уплате</Text>
          <Flex gap={1} align="center">
            <Text variant="lg" weight="bold" color="success">
              {formatRub(data.tax_due)}
            </Text>
            <Text variant="xs" color="muted">({data.applicable_rate || '—'})</Text>
          </Flex>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">НДС накоплено</Text>
          <Text variant="md">{formatRub(data.vat_accumulated)}</Text>
        </div>
        <div className={styles.statCell}>
          <Text variant="xs" color="secondary">НДФЛ удержано</Text>
          <Text variant="md">{formatRub(data.ndfl_withheld)}</Text>
        </div>
      </div>
    </div>
  )
}
