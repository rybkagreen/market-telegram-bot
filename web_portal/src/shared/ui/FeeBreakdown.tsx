interface FeeRow {
  label: string
  value: string
}

interface FeeBreakdownProps {
  rows?: FeeRow[]
  total?: { label: string; value: string }
}

export function FeeBreakdown({ rows, total }: FeeBreakdownProps) {
  if (!rows?.length && !total) return null

  return (
    <div className="bg-harbor-card border border-border rounded-lg shadow-sm overflow-hidden">
      <table className="w-full text-sm">
        <tbody className="divide-y divide-border">
          {rows?.map((row, i) => (
            <tr key={i}>
              <td className="px-5 py-2.5 text-text-secondary">{row.label}</td>
              <td className="px-5 py-2.5 text-right font-mono text-text-primary tabular-nums">{row.value}</td>
            </tr>
          ))}
          {total && (
            <tr className="bg-harbor-elevated/50 font-semibold">
              <td className="px-5 py-3 text-text-primary">{total.label}</td>
              <td className="px-5 py-3 text-right font-mono text-text-primary tabular-nums">{total.value}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
