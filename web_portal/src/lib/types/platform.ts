export interface PlatformSettings {
  legal_name: string | null
  inn: string | null
  kpp: string | null
  ogrn: string | null
  address: string | null
  bank_name: string | null
  bank_account: string | null
  bank_bik: string | null
  bank_corr_account: string | null
}

export type PlatformSettingsPayload = Partial<PlatformSettings>
