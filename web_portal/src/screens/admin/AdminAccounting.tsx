import TaxSummaryBase from '@components/admin/TaxSummaryBase'

export default function AdminAccounting() {
  return (
    <TaxSummaryBase
      title="Бухгалтерия"
      subtitle="КУДиР, УСН-15%, НДС и НДФЛ платформы за выбранный квартал"
      crumbs={['Администратор', 'Бухгалтерия']}
      coloredKpis={false}
      showEmptyHint
      downloadMode="auth"
    />
  )
}
