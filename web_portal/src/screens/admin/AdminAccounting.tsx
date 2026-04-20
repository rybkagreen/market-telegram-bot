import TaxSummaryBase from '@components/admin/TaxSummaryBase'

export default function AdminAccounting() {
  return (
    <TaxSummaryBase
      title="Бухгалтерия"
      subtitle="КУДиР, УСН-15%, НДС и НДФЛ платформы за выбранный квартал"
      coloredKpis={false}
      showEmptyHint
      downloadMode="auth"
    />
  )
}
