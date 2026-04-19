export type ContractType =
  | 'owner_service'
  | 'advertiser_campaign'
  | 'advertiser_framework'
  | 'platform_rules'
  | 'privacy_policy'
  | 'tax_agreement'

export type ContractRole = 'owner' | 'advertiser'

export type ContractStatus = 'draft' | 'pending' | 'signed' | 'expired' | 'cancelled'

export type SignatureMethod = 'button_accept' | 'sms_code'

export interface Contract {
  id: number
  user_id: number
  contract_type: ContractType
  contract_status: ContractStatus
  placement_request_id: number | null
  template_version: string
  signature_method: SignatureMethod | null
  signed_at: string | null
  expires_at: string | null
  pdf_url: string | null
  kep_requested: boolean
  kep_request_email: string | null
  role: ContractRole | null
  created_at: string
  updated_at: string
}
