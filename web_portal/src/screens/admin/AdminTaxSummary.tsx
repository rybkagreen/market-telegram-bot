import { Card } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import TaxSummaryBase, { type KudirEntry } from '@components/admin/TaxSummaryBase'

function formatDate(dt: string): string {
  return formatDateMSK(dt)
}

function KudirTable({ entries }: { entries: KudirEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-text-secondary">Записей нет</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-border text-text-secondary">
            <th className="pb-2 pr-3">№</th>
            <th className="pb-2 pr-3">Дата</th>
            <th className="pb-2 pr-3">Операция</th>
            <th className="pb-2 pr-3 text-right">Доход</th>
            <th className="pb-2 text-right">Расход</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.entry_number} className="border-b border-border/50 hover:bg-harbor-elevated">
              <td className="py-1.5 pr-3 text-text-tertiary">{e.entry_number}</td>
              <td className="py-1.5 pr-3 text-text-secondary whitespace-nowrap">{formatDate(e.operation_date)}</td>
              <td className="py-1.5 pr-3 text-text-primary max-w-xs truncate">{e.description}</td>
              <td className="py-1.5 pr-3 text-right text-success font-mono">
                {parseFloat(e.income_amount) > 0
                  ? parseFloat(e.income_amount).toLocaleString('ru-RU', { minimumFractionDigits: 2 }) + ' ₽'
                  : '—'}
              </td>
              <td className="py-1.5 text-right text-danger font-mono">
                {e.expense_amount && parseFloat(e.expense_amount) > 0
                  ? parseFloat(e.expense_amount).toLocaleString('ru-RU', { minimumFractionDigits: 2 }) + ' ₽'
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function AdminTaxSummary() {
  return (
    <TaxSummaryBase
      title="📊 Налоговая отчётность"
      coloredKpis
      showEmptyHint={false}
      downloadMode="auth"
    >
      {(data) =>
        data.kudir_entries && data.kudir_entries.length >= 0 ? (
          <Card title={`📋 КУДиР — ${data.year} / Q${data.quarter} (${data.kudir_entries.length} записей)`}>
            <KudirTable entries={data.kudir_entries} />
          </Card>
        ) : null
      }
    </TaxSummaryBase>
  )
}
