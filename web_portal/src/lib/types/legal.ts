export type LegalStatus =
  | 'legal_entity'
  | 'individual_entrepreneur'
  | 'self_employed'
  | 'individual'

export type TaxRegime = 'osno' | 'usn' | 'usn_d' | 'usn_dr' | 'patent' | 'npd' | 'ndfl'

export interface LegalProfile {
  id: number
  user_id: number
  legal_status: LegalStatus
  inn: string | null
  kpp: string | null
  ogrn: string | null
  ogrnip: string | null
  legal_name: string | null
  address: string | null
  tax_regime: TaxRegime | null
  bank_name: string | null
  bank_account: string | null
  bank_bik: string | null
  bank_corr_account: string | null
  yoomoney_wallet: string | null
  passport_series: string | null
  passport_number: string | null
  passport_issued_by: string | null
  passport_issued_at: string | null
  has_passport_data: boolean
  has_inn_scan: boolean
  has_passport_scan: boolean
  has_self_employed_cert: boolean
  has_company_doc: boolean
  is_verified: boolean
  is_complete: boolean
  created_at: string
  updated_at: string
}

export interface LegalProfileCreate {
  legal_status: LegalStatus
  inn?: string
  kpp?: string
  ogrn?: string
  ogrnip?: string
  legal_name?: string
  address?: string
  tax_regime?: TaxRegime
  bank_name?: string
  bank_account?: string
  bank_bik?: string
  bank_corr_account?: string
  yoomoney_wallet?: string
  passport_series?: string
  passport_number?: string
  passport_issued_by?: string
  passport_issue_date?: string
}

export interface RequiredFields {
  fields: string[]
  scans: string[]
  show_bank_details: boolean
  show_passport: boolean
  show_yoomoney: boolean
  tax_regime_required: boolean
}
