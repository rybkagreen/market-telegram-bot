import { formatCurrency } from '@/lib/formatters'
import type { LegalStatus, TaxRegime } from '@/lib/types'

const TAX_REGIME_LABELS: Record<TaxRegime, string> = {
  osno: 'ОСНО',
  usn: 'УСН',
  usn_d: 'УСН (доходы)',
  usn_dr: 'УСН (доходы − расходы)',
  patent: 'Патент (ПСН)',
  npd: 'НПД',
  ndfl: 'НДФЛ',
}

interface TaxBreakdownProps {
  grossAmount: number
  legalStatus: LegalStatus
  taxRegime?: TaxRegime
}

export function TaxBreakdown({ grossAmount, legalStatus, taxRegime }: TaxBreakdownProps) {
  const boxStyle: React.CSSProperties = {
    padding: '12px 16px',
    borderRadius: 'var(--rh-radius-md, 12px)',
    background: 'var(--rh-surface, rgba(255,255,255,0.04))',
    fontSize: 'var(--rh-text-sm, 14px)',
  }
  const rowStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: 4,
  }
  const mutedStyle: React.CSSProperties = { color: 'var(--rh-text-muted, rgba(255,255,255,0.5))' }

  if (legalStatus === 'individual') {
    const tax = Math.round(grossAmount * 0.13 * 100) / 100
    const net = grossAmount - tax
    return (
      <div style={boxStyle}>
        <div style={rowStyle}>
          <span style={mutedStyle}>Начислено</span>
          <span>{formatCurrency(grossAmount)}</span>
        </div>
        <div style={rowStyle}>
          <span style={mutedStyle}>НДФЛ 13%</span>
          <span style={{ color: 'var(--rh-danger, #f87171)' }}>−{formatCurrency(tax)}</span>
        </div>
        <div style={{ ...rowStyle, marginBottom: 0 }}>
          <span style={{ fontWeight: 600 }}>К выплате</span>
          <span style={{ fontWeight: 600, color: 'var(--rh-success, #4ade80)' }}>{formatCurrency(net)}</span>
        </div>
      </div>
    )
  }

  if (legalStatus === 'legal_entity') {
    return (
      <div style={boxStyle}>
        <span style={mutedStyle}>К выплате: </span>
        <span>{formatCurrency(grossAmount)} (сумма включает НДС 22%)</span>
      </div>
    )
  }

  if (legalStatus === 'individual_entrepreneur') {
    const regimeLabel = taxRegime ? TAX_REGIME_LABELS[taxRegime] : '—'
    return (
      <div style={boxStyle}>
        <span style={mutedStyle}>К выплате: </span>
        <span>{formatCurrency(grossAmount)} (налог по {regimeLabel} уплачивается вами самостоятельно)</span>
      </div>
    )
  }

  // self_employed
  return (
    <div style={boxStyle}>
      <span style={mutedStyle}>К выплате: </span>
      <span>{formatCurrency(grossAmount)} (НПД 6% вы уплачиваете самостоятельно через «Мой налог»)</span>
    </div>
  )
}
