import { Icon } from '@shared/ui'
import { formatDateMSK } from '@/lib/constants'
import TaxSummaryBase, { type KudirEntry } from '@components/admin/TaxSummaryBase'

function KudirTable({ entries }: { entries: KudirEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-[13px] text-text-secondary">Записей нет</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-harbor-secondary">
          <tr className="text-[11px] uppercase tracking-[0.08em] text-text-tertiary font-semibold">
            <th className="text-left px-4 py-2.5 w-12">№</th>
            <th className="text-left px-4 py-2.5">Дата</th>
            <th className="text-left px-4 py-2.5">Операция</th>
            <th className="text-right px-4 py-2.5">Доход</th>
            <th className="text-right px-4 py-2.5">Расход</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {entries.map((e) => {
            const income = parseFloat(e.income_amount)
            const expense = e.expense_amount ? parseFloat(e.expense_amount) : 0
            return (
              <tr key={e.entry_number} className="hover:bg-harbor-elevated/40 transition-colors">
                <td className="px-4 py-3 text-text-tertiary font-mono tabular-nums">
                  {e.entry_number}
                </td>
                <td className="px-4 py-3 text-text-secondary whitespace-nowrap tabular-nums">
                  {formatDateMSK(e.operation_date)}
                </td>
                <td className="px-4 py-3 text-text-primary max-w-md truncate">
                  {e.description}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-success">
                  {income > 0
                    ? `${income.toLocaleString('ru-RU', { minimumFractionDigits: 2 })} ₽`
                    : '—'}
                </td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-danger">
                  {expense > 0
                    ? `${expense.toLocaleString('ru-RU', { minimumFractionDigits: 2 })} ₽`
                    : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function AdminTaxSummary() {
  return (
    <TaxSummaryBase
      title="Налоговая отчётность"
      subtitle="КУДиР и ключевые налоговые показатели за выбранный квартал"
      coloredKpis
      showEmptyHint={false}
      downloadMode="auth"
    >
      {(data) =>
        data.kudir_entries && data.kudir_entries.length >= 0 ? (
          <div className="bg-harbor-card border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-border flex items-center gap-2">
              <Icon name="docs" size={14} className="text-text-tertiary" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                КУДиР — {data.year} / Q{data.quarter}
              </span>
              <span className="ml-auto text-[11px] text-text-tertiary font-mono tabular-nums">
                {data.kudir_entries.length} записей
              </span>
            </div>
            <KudirTable entries={data.kudir_entries} />
          </div>
        ) : null
      }
    </TaxSummaryBase>
  )
}
