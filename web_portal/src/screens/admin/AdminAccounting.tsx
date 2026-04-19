import TaxSummaryBase from '@components/admin/TaxSummaryBase'

export default function AdminAccounting() {
  return (
    <TaxSummaryBase
      title="📊 Бухгалтерия"
      coloredKpis={false}
      showEmptyHint
      downloadMode="auth"
    />
  )
}
