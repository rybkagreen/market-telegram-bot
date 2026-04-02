# RekHarborBot — Document Automation & Video Support Spec v1.0

**Date:** 2026-03-22  
**Purpose:** Single source of truth for DB ↔ API ↔ Mini App ↔ Bot consistency  
**Rule:** If this doc says field is `legal_status`, then DB column, Pydantic schema, API response, TS type, and UI label ALL use `legal_status`. No aliases, no deviations.

---

## 0. SHARED ENUMS (used identically across all layers)

### 0.1 LegalStatus
```
DB column type:   VARCHAR(30)
Python enum name: LegalStatus
TS type name:     LegalStatus

Values:
  "legal_entity"    → UI: "Юридическое лицо"
  "individual_entrepreneur" → UI: "Индивидуальный предприниматель"  
  "self_employed"   → UI: "Самозанятый"
  "individual"      → UI: "Физическое лицо"
```

### 0.2 TaxRegime
```
DB column type:   VARCHAR(20) | NULL
Python enum name: TaxRegime
TS type name:     TaxRegime

Values:
  "osno"    → UI: "ОСНО (общая)"
  "usn"     → UI: "УСН (упрощённая)"
  "usn_d"   → UI: "УСН доходы"
  "usn_dr"  → UI: "УСН доходы минус расходы"
  "patent"  → UI: "Патент (ПСН)"
  "npd"     → UI: "НПД (самозанятый)"     # auto-set for self_employed
  "ndfl"    → UI: "НДФЛ"                   # auto-set for individual
```

### 0.3 ContractType
```
DB column type:   VARCHAR(30)
Python enum name: ContractType
TS type name:     ContractType

Values:
  "owner_service"        → UI: "Договор оказания услуг (владелец)"
  "advertiser_campaign"  → UI: "Договор на размещение рекламы"
  "platform_rules"       → UI: "Правила платформы"
  "privacy_policy"       → UI: "Политика конфиденциальности"
  "tax_agreement"        → UI: "Соглашение о налоговых обязательствах"
```

### 0.4 ContractStatus
```
DB column type:   VARCHAR(20)
Python enum name: ContractStatus
TS type name:     ContractStatus

Values:
  "draft"       → UI: "Черновик"
  "pending"     → UI: "Ожидает подписания"
  "signed"      → UI: "Подписан"
  "expired"     → UI: "Истёк"
  "cancelled"   → UI: "Отменён"
```

### 0.5 SignatureMethod
```
DB column type:   VARCHAR(20) | NULL
Python enum name: SignatureMethod
TS type name:     SignatureMethod

Values:
  "button_accept"   → UI: "Нажатие кнопки"
  "sms_code"        → UI: "СМС-код"
```

### 0.6 OrdStatus
```
DB column type:   VARCHAR(20)
Python enum name: OrdStatus
TS type name:     OrdStatus

Values:
  "pending"          → UI: "Ожидание"
  "registered"       → UI: "Зарегистрирован"
  "token_received"   → UI: "Токен получен"
  "reported"         → UI: "Отчёт отправлен"
  "failed"           → UI: "Ошибка"
```

### 0.7 MediaType (NEW — for video support)
```
DB column type:   VARCHAR(10)
Python enum name: MediaType
TS type name:     MediaType

Values:
  "none"    → no media attached
  "photo"   → image attached
  "video"   → video attached
```

---

## 1. DATABASE MODELS

### 1.1 `legal_profiles` table (NEW)

| Column | Type | Nullable | Default | Constraint | Notes |
|--------|------|----------|---------|------------|-------|
| id | SERIAL | NO | auto | PK | |
| user_id | BIGINT | NO | — | FK→users.id, UNIQUE | one-to-one |
| legal_status | VARCHAR(30) | NO | — | — | LegalStatus enum |
| inn | VARCHAR(12) | YES | NULL | — | 10 digits for ЮЛ, 12 for rest |
| kpp | VARCHAR(9) | YES | NULL | — | only legal_entity |
| ogrn | VARCHAR(15) | YES | NULL | — | 13 digits ЮЛ |
| ogrnip | VARCHAR(15) | YES | NULL | — | 15 digits ИП |
| legal_name | VARCHAR(500) | YES | NULL | — | org name or full name |
| address | TEXT | YES | NULL | — | legal address |
| tax_regime | VARCHAR(20) | YES | NULL | — | TaxRegime enum |
| bank_name | VARCHAR(200) | YES | NULL | — | ЮЛ, ИП |
| bank_account | VARCHAR(20) | YES | NULL | — | р/с 20 digits |
| bank_bik | VARCHAR(9) | YES | NULL | — | БИК 9 digits |
| bank_corr_account | VARCHAR(20) | YES | NULL | — | к/с 20 digits |
| yoomoney_wallet | VARCHAR(50) | YES | NULL | — | self_employed |
| passport_series | VARCHAR(4) | YES | NULL | — | individual |
| passport_number | VARCHAR(6) | YES | NULL | — | individual |
| passport_issued_by | TEXT | YES | NULL | — | individual |
| passport_issue_date | DATE | YES | NULL | — | individual |
| inn_scan_file_id | VARCHAR(200) | YES | NULL | — | Telegram file_id |
| passport_scan_file_id | VARCHAR(200) | YES | NULL | — | Telegram file_id |
| self_employed_cert_file_id | VARCHAR(200) | YES | NULL | — | Telegram file_id |
| company_doc_file_id | VARCHAR(200) | YES | NULL | — | Устав/выписка ЕГРЮЛ |
| is_verified | BOOLEAN | NO | FALSE | — | admin/auto verified |
| verified_at | TIMESTAMP | YES | NULL | — | |
| created_at | TIMESTAMP | NO | now() | — | |
| updated_at | TIMESTAMP | NO | now() | — | |

**Indexes:**
- `ix_legal_profiles_user_id` UNIQUE on user_id
- `ix_legal_profiles_inn` on inn

### 1.2 `contracts` table (NEW)

| Column | Type | Nullable | Default | Constraint | Notes |
|--------|------|----------|---------|------------|-------|
| id | SERIAL | NO | auto | PK | |
| user_id | BIGINT | NO | — | FK→users.id | |
| contract_type | VARCHAR(30) | NO | — | — | ContractType enum |
| contract_status | VARCHAR(20) | NO | "draft" | — | ContractStatus enum |
| placement_request_id | INTEGER | YES | NULL | FK→placement_requests.id | only advertiser_campaign |
| legal_status_snapshot | JSONB | YES | NULL | — | frozen copy of LegalProfile at signing |
| template_version | VARCHAR(20) | NO | "1.0" | — | for template evolution |
| pdf_file_path | VARCHAR(500) | YES | NULL | — | path on server |
| pdf_telegram_file_id | VARCHAR(200) | YES | NULL | — | Telegram file_id of PDF |
| signature_method | VARCHAR(20) | YES | NULL | — | SignatureMethod enum |
| signature_ip | VARCHAR(45) | YES | NULL | — | IPv4/IPv6 |
| signed_at | TIMESTAMP | YES | NULL | — | |
| expires_at | TIMESTAMP | YES | NULL | — | for campaign contracts |
| created_at | TIMESTAMP | NO | now() | — | |
| updated_at | TIMESTAMP | NO | now() | — | |

**Indexes:**
- `ix_contracts_user_id` on user_id
- `ix_contracts_placement_request_id` on placement_request_id
- `ix_contracts_type_status` on (contract_type, contract_status)

### 1.3 `ord_registrations` table (NEW)

| Column | Type | Nullable | Default | Constraint | Notes |
|--------|------|----------|---------|------------|-------|
| id | SERIAL | NO | auto | PK | |
| placement_request_id | INTEGER | NO | — | FK→placement_requests.id, UNIQUE | |
| contract_id | INTEGER | YES | NULL | FK→contracts.id | |
| advertiser_ord_id | VARCHAR(100) | YES | NULL | — | ID in ORD system |
| creative_ord_id | VARCHAR(100) | YES | NULL | — | creative ID in ORD |
| erid | VARCHAR(100) | YES | NULL | — | ad token for marking |
| ord_provider | VARCHAR(50) | NO | "default" | — | which ORD provider |
| status | VARCHAR(20) | NO | "pending" | — | OrdStatus enum |
| registered_at | TIMESTAMP | YES | NULL | — | |
| token_received_at | TIMESTAMP | YES | NULL | — | |
| reported_at | TIMESTAMP | YES | NULL | — | |
| error_message | TEXT | YES | NULL | — | |
| created_at | TIMESTAMP | NO | now() | — | |
| updated_at | TIMESTAMP | NO | now() | — | |

**Indexes:**
- `ix_ord_registrations_placement_request_id` UNIQUE
- `ix_ord_registrations_erid` on erid

### 1.4 Changes to `users` table

| New Column | Type | Nullable | Default | Notes |
|-----------|------|----------|---------|-------|
| legal_status_completed | BOOLEAN | NO | FALSE | all legal fields filled |
| legal_profile_prompted_at | TIMESTAMP | YES | NULL | when first-start prompt was shown |
| legal_profile_skipped_at | TIMESTAMP | YES | NULL | when user clicked "Заполнить позже" |
| platform_rules_accepted_at | TIMESTAMP | YES | NULL | |
| privacy_policy_accepted_at | TIMESTAMP | YES | NULL | |

### 1.5 Changes to `placement_requests` table (VIDEO SUPPORT)

| New Column | Type | Nullable | Default | Notes |
|-----------|------|----------|---------|-------|
| media_type | VARCHAR(10) | NO | "none" | MediaType: none/photo/video |
| video_file_id | VARCHAR(200) | YES | NULL | Telegram file_id for video |
| video_url | VARCHAR(500) | YES | NULL | direct URL if available |
| video_thumbnail_file_id | VARCHAR(200) | YES | NULL | thumbnail Telegram file_id |
| video_duration | INTEGER | YES | NULL | seconds |
| erid | VARCHAR(100) | YES | NULL | ad marking token (copied from ord_registrations) |

**NOTE:** Existing `image_file_id` field (if present) continues to work. The new `media_type` disambiguates what to publish.

---

## 2. API SCHEMAS (Pydantic v2)

### 2.1 `src/api/schemas/legal_profile.py`

```python
# === Enums (also exported for TS codegen) ===
class LegalStatus(str, Enum):
    legal_entity = "legal_entity"
    individual_entrepreneur = "individual_entrepreneur"
    self_employed = "self_employed"
    individual = "individual"

class TaxRegime(str, Enum):
    osno = "osno"
    usn = "usn"
    usn_d = "usn_d"
    usn_dr = "usn_dr"
    patent = "patent"
    npd = "npd"
    ndfl = "ndfl"

# === Request schemas ===
class LegalProfileCreate(BaseModel):
    legal_status: LegalStatus
    inn: str | None = None                        # validated: 10 or 12 digits
    kpp: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    legal_name: str | None = None
    address: str | None = None
    tax_regime: TaxRegime | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    bank_bik: str | None = None
    bank_corr_account: str | None = None
    yoomoney_wallet: str | None = None
    passport_series: str | None = None
    passport_number: str | None = None
    passport_issued_by: str | None = None
    passport_issue_date: date | None = None

class LegalProfileUpdate(BaseModel):
    """All fields optional for partial update"""
    legal_status: LegalStatus | None = None
    inn: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    legal_name: str | None = None
    address: str | None = None
    tax_regime: TaxRegime | None = None
    bank_name: str | None = None
    bank_account: str | None = None
    bank_bik: str | None = None
    bank_corr_account: str | None = None
    yoomoney_wallet: str | None = None
    passport_series: str | None = None
    passport_number: str | None = None
    passport_issued_by: str | None = None
    passport_issue_date: date | None = None

class ScanUpload(BaseModel):
    scan_type: Literal["inn", "passport", "self_employed_cert", "company_doc"]
    file_id: str  # Telegram file_id

# === Response schemas ===
class LegalProfileResponse(BaseModel):
    id: int
    user_id: int
    legal_status: LegalStatus
    inn: str | None
    kpp: str | None
    ogrn: str | None
    ogrnip: str | None
    legal_name: str | None
    address: str | None
    tax_regime: TaxRegime | None
    bank_name: str | None
    bank_account: str | None
    bank_bik: str | None
    bank_corr_account: str | None
    yoomoney_wallet: str | None
    # passport fields NOT returned via API (sensitive)
    has_passport_data: bool  # computed: passport_series is not None
    has_inn_scan: bool       # computed: inn_scan_file_id is not None
    has_passport_scan: bool
    has_self_employed_cert: bool
    has_company_doc: bool
    is_verified: bool
    is_complete: bool        # computed: all required fields for status are filled
    created_at: datetime
    updated_at: datetime
```

### 2.2 `src/api/schemas/contract.py`

```python
class ContractType(str, Enum):
    owner_service = "owner_service"
    advertiser_campaign = "advertiser_campaign"
    platform_rules = "platform_rules"
    privacy_policy = "privacy_policy"
    tax_agreement = "tax_agreement"

class ContractStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    signed = "signed"
    expired = "expired"
    cancelled = "cancelled"

class SignatureMethod(str, Enum):
    button_accept = "button_accept"
    sms_code = "sms_code"

# === Request ===
class ContractSignRequest(BaseModel):
    signature_method: SignatureMethod
    sms_code: str | None = None  # required if method == sms_code

class AcceptRulesRequest(BaseModel):
    """Accept platform rules + privacy policy in one action"""
    accept_platform_rules: bool
    accept_privacy_policy: bool

# === Response ===
class ContractResponse(BaseModel):
    id: int
    user_id: int
    contract_type: ContractType
    contract_status: ContractStatus
    placement_request_id: int | None
    template_version: str
    signature_method: SignatureMethod | None
    signed_at: datetime | None
    expires_at: datetime | None
    pdf_url: str | None          # generated download URL
    created_at: datetime
    updated_at: datetime

class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int
```

### 2.3 Changes to `src/api/schemas/placement.py` (VIDEO)

```python
class MediaType(str, Enum):
    none = "none"
    photo = "photo"
    video = "video"

# Add to PlacementCreateRequest:
class PlacementCreateRequest(BaseModel):
    # ... existing fields ...
    media_type: MediaType = MediaType.none
    video_file_id: str | None = None
    video_url: str | None = None
    video_duration: int | None = None  # seconds

# Add to PlacementResponse:
class PlacementResponse(BaseModel):
    # ... existing fields ...
    media_type: MediaType
    video_file_id: str | None
    video_url: str | None
    video_thumbnail_file_id: str | None
    video_duration: int | None
    erid: str | None  # ad marking token
```

### 2.4 `src/api/schemas/ord.py`

```python
class OrdStatus(str, Enum):
    pending = "pending"
    registered = "registered"
    token_received = "token_received"
    reported = "reported"
    failed = "failed"

class OrdRegistrationResponse(BaseModel):
    id: int
    placement_request_id: int
    erid: str | None
    status: OrdStatus
    ord_provider: str
    error_message: str | None
    created_at: datetime
```

---

## 3. API ENDPOINTS

### 3.1 Legal Profile — `src/api/routers/legal_profile.py`

| Method | Path | Handler | Request | Response | Auth | Notes |
|--------|------|---------|---------|----------|------|-------|
| GET | `/api/legal-profile/me` | `get_my_profile` | — | `LegalProfileResponse \| null` | JWT | |
| POST | `/api/legal-profile` | `create_profile` | `LegalProfileCreate` | `LegalProfileResponse` | JWT | |
| PATCH | `/api/legal-profile` | `update_profile` | `LegalProfileUpdate` | `LegalProfileResponse` | JWT | partial update |
| POST | `/api/legal-profile/scan` | `upload_scan` | `ScanUpload` | `{success: true}` | JWT | |
| GET | `/api/legal-profile/required-fields` | `get_required_fields` | `?legal_status=...` | `RequiredFieldsResponse` | JWT | tells UI which fields to show |
| POST | `/api/legal-profile/validate-inn` | `validate_inn` | `{inn: str}` | `{valid: bool, type: str}` | JWT | checksum validation |

### 3.2 Contracts — `src/api/routers/contracts.py`

| Method | Path | Handler | Request | Response | Auth | Notes |
|--------|------|---------|---------|----------|------|-------|
| GET | `/api/contracts` | `list_contracts` | `?type=&status=` | `ContractListResponse` | JWT | |
| GET | `/api/contracts/{id}` | `get_contract` | — | `ContractResponse` | JWT | |
| POST | `/api/contracts/generate` | `generate_contract` | `{contract_type, placement_request_id?}` | `ContractResponse` | JWT | |
| POST | `/api/contracts/{id}/sign` | `sign_contract` | `ContractSignRequest` | `ContractResponse` | JWT | |
| GET | `/api/contracts/{id}/pdf` | `download_pdf` | — | PDF file | JWT | StreamingResponse |
| POST | `/api/contracts/accept-rules` | `accept_rules` | `AcceptRulesRequest` | `{success: true}` | JWT | platform rules + privacy |

### 3.3 ORD — `src/api/routers/ord.py`

| Method | Path | Handler | Request | Response | Auth | Notes |
|--------|------|---------|---------|----------|------|-------|
| GET | `/api/ord/{placement_request_id}` | `get_ord_status` | — | `OrdRegistrationResponse` | JWT | |
| POST | `/api/ord/register` | `register_creative` | `{placement_request_id}` | `OrdRegistrationResponse` | JWT | triggers async registration |

### 3.4 Changes to existing `/api/placements` (VIDEO)

| Method | Path | Change | Notes |
|--------|------|--------|-------|
| POST | `/api/placements` | Add `media_type`, `video_file_id`, `video_url`, `video_duration` to request | |
| GET | `/api/placements/{id}` | Add `media_type`, `video_*`, `erid` to response | |
| GET | `/api/placements` | Add `media_type`, `video_*`, `erid` to list items | |

### 3.5 Changes to existing `/api/users`

| Method | Path | Change | Notes |
|--------|------|--------|-------|
| GET | `/api/users/me` | Add `legal_status_completed`, `legal_profile_prompted_at`, `legal_profile_skipped_at`, `platform_rules_accepted_at`, `privacy_policy_accepted_at`, `has_legal_profile` to response | |
| POST | `/api/users/skip-legal-prompt` | NEW: set `legal_profile_prompted_at` and `legal_profile_skipped_at` | Returns `{success: true}` |

---

## 4. MINI APP — TypeScript Types

### 4.1 `mini_app/src/lib/types.ts` — NEW types

```typescript
// === Enums ===
export type LegalStatus = 
  | 'legal_entity' 
  | 'individual_entrepreneur' 
  | 'self_employed' 
  | 'individual';

export type TaxRegime = 
  | 'osno' | 'usn' | 'usn_d' | 'usn_dr' | 'patent' | 'npd' | 'ndfl';

export type ContractType = 
  | 'owner_service' 
  | 'advertiser_campaign' 
  | 'platform_rules' 
  | 'privacy_policy' 
  | 'tax_agreement';

export type ContractStatus = 'draft' | 'pending' | 'signed' | 'expired' | 'cancelled';

export type SignatureMethod = 'button_accept' | 'sms_code';

export type OrdStatus = 'pending' | 'registered' | 'token_received' | 'reported' | 'failed';

export type MediaType = 'none' | 'photo' | 'video';

// === Interfaces ===
export interface LegalProfile {
  id: number;
  user_id: number;
  legal_status: LegalStatus;
  inn: string | null;
  kpp: string | null;
  ogrn: string | null;
  ogrnip: string | null;
  legal_name: string | null;
  address: string | null;
  tax_regime: TaxRegime | null;
  bank_name: string | null;
  bank_account: string | null;
  bank_bik: string | null;
  bank_corr_account: string | null;
  yoomoney_wallet: string | null;
  has_passport_data: boolean;
  has_inn_scan: boolean;
  has_passport_scan: boolean;
  has_self_employed_cert: boolean;
  has_company_doc: boolean;
  is_verified: boolean;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface LegalProfileCreate {
  legal_status: LegalStatus;
  inn?: string;
  kpp?: string;
  ogrn?: string;
  ogrnip?: string;
  legal_name?: string;
  address?: string;
  tax_regime?: TaxRegime;
  bank_name?: string;
  bank_account?: string;
  bank_bik?: string;
  bank_corr_account?: string;
  yoomoney_wallet?: string;
  passport_series?: string;
  passport_number?: string;
  passport_issued_by?: string;
  passport_issue_date?: string;
}

export interface Contract {
  id: number;
  user_id: number;
  contract_type: ContractType;
  contract_status: ContractStatus;
  placement_request_id: number | null;
  template_version: string;
  signature_method: SignatureMethod | null;
  signed_at: string | null;
  expires_at: string | null;
  pdf_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrdRegistration {
  id: number;
  placement_request_id: number;
  erid: string | null;
  status: OrdStatus;
  ord_provider: string;
  error_message: string | null;
  created_at: string;
}

export interface RequiredFields {
  fields: string[];           // field names that are required
  scans: string[];            // scan types that are required
  show_bank_details: boolean;
  show_passport: boolean;
  show_yoomoney: boolean;
  tax_regime_required: boolean;
}

// === Extension to existing Placement type ===
// Add to existing PlacementRequest interface:
//   media_type: MediaType;
//   video_file_id: string | null;
//   video_url: string | null;
//   video_thumbnail_file_id: string | null;
//   video_duration: number | null;
//   erid: string | null;

// === Extension to existing User type ===
// Add to existing User interface:
//   legal_status_completed: boolean;
//   legal_profile_prompted_at: string | null;
//   legal_profile_skipped_at: string | null;
//   platform_rules_accepted_at: string | null;
//   privacy_policy_accepted_at: string | null;
//   has_legal_profile: boolean;
```

---

## 5. MINI APP — API Clients

### 5.1 `mini_app/src/api/legalProfile.ts` (NEW)

```typescript
import { ky } from './client';
import type { LegalProfile, LegalProfileCreate, RequiredFields } from '@/lib/types';

export const legalProfileApi = {
  getMyProfile: () => 
    ky.get('legal-profile/me').json<LegalProfile | null>(),

  createProfile: (data: LegalProfileCreate) => 
    ky.post('legal-profile', { json: data }).json<LegalProfile>(),

  updateProfile: (data: Partial<LegalProfileCreate>) => 
    ky.patch('legal-profile', { json: data }).json<LegalProfile>(),

  uploadScan: (scanType: string, fileId: string) => 
    ky.post('legal-profile/scan', { json: { scan_type: scanType, file_id: fileId } }).json<{ success: boolean }>(),

  getRequiredFields: (legalStatus: LegalStatus) => 
    ky.get('legal-profile/required-fields', { searchParams: { legal_status: legalStatus } }).json<RequiredFields>(),

  validateInn: (inn: string) => 
    ky.post('legal-profile/validate-inn', { json: { inn } }).json<{ valid: boolean; type: string }>(),
};
```

### 5.2 `mini_app/src/api/contracts.ts` (NEW)

```typescript
import { ky } from './client';
import type { Contract, ContractType, SignatureMethod } from '@/lib/types';

export const contractsApi = {
  list: (params?: { type?: ContractType; status?: string }) => 
    ky.get('contracts', { searchParams: params ?? {} }).json<{ items: Contract[]; total: number }>(),

  get: (id: number) => 
    ky.get(`contracts/${id}`).json<Contract>(),

  generate: (contractType: ContractType, placementRequestId?: number) => 
    ky.post('contracts/generate', { json: { contract_type: contractType, placement_request_id: placementRequestId } }).json<Contract>(),

  sign: (id: number, method: SignatureMethod, smsCode?: string) => 
    ky.post(`contracts/${id}/sign`, { json: { signature_method: method, sms_code: smsCode } }).json<Contract>(),

  getPdfUrl: (id: number) => 
    `${ky.defaults?.prefixUrl ?? ''}/contracts/${id}/pdf`,

  acceptRules: (acceptPlatformRules: boolean, acceptPrivacyPolicy: boolean) => 
    ky.post('contracts/accept-rules', { json: { accept_platform_rules: acceptPlatformRules, accept_privacy_policy: acceptPrivacyPolicy } }).json<{ success: boolean }>(),
};
```

### 5.3 `mini_app/src/api/ord.ts` (NEW)

```typescript
import { ky } from './client';
import type { OrdRegistration } from '@/lib/types';

export const ordApi = {
  getStatus: (placementRequestId: number) => 
    ky.get(`ord/${placementRequestId}`).json<OrdRegistration>(),

  register: (placementRequestId: number) => 
    ky.post('ord/register', { json: { placement_request_id: placementRequestId } }).json<OrdRegistration>(),
};
```

---

## 6. MINI APP — TanStack Query Hooks

### 6.1 `mini_app/src/hooks/useLegalProfileQueries.ts` (NEW)

```typescript
export function useMyLegalProfile() {
  return useQuery({
    queryKey: ['legal-profile', 'me'],
    queryFn: () => legalProfileApi.getMyProfile(),
  });
}

export function useRequiredFields(legalStatus: LegalStatus | undefined) {
  return useQuery({
    queryKey: ['legal-profile', 'required-fields', legalStatus],
    queryFn: () => legalProfileApi.getRequiredFields(legalStatus!),
    enabled: !!legalStatus,
  });
}

export function useCreateLegalProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LegalProfileCreate) => legalProfileApi.createProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['legal-profile'] });
      qc.invalidateQueries({ queryKey: ['users', 'me'] });
    },
  });
}

export function useUpdateLegalProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<LegalProfileCreate>) => legalProfileApi.updateProfile(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['legal-profile'] }),
  });
}

export function useValidateInn() {
  return useMutation({
    mutationFn: (inn: string) => legalProfileApi.validateInn(inn),
  });
}

export function useSkipLegalPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => ky.post('users/skip-legal-prompt').json<{ success: boolean }>(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'me'] }),
  });
}
```

### 6.2 `mini_app/src/hooks/useContractQueries.ts` (NEW)

```typescript
export function useContracts(type?: ContractType) {
  return useQuery({
    queryKey: ['contracts', { type }],
    queryFn: () => contractsApi.list(type ? { type } : undefined),
  });
}

export function useContract(id: number) {
  return useQuery({
    queryKey: ['contracts', id],
    queryFn: () => contractsApi.get(id),
    enabled: id > 0,
  });
}

export function useGenerateContract() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contractType, placementRequestId }: { contractType: ContractType; placementRequestId?: number }) =>
      contractsApi.generate(contractType, placementRequestId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contracts'] }),
  });
}

export function useSignContract() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, method, smsCode }: { id: number; method: SignatureMethod; smsCode?: string }) =>
      contractsApi.sign(id, method, smsCode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['contracts'] });
      qc.invalidateQueries({ queryKey: ['users', 'me'] });
    },
  });
}

export function useAcceptRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => contractsApi.acceptRules(true, true),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users', 'me'] }),
  });
}
```

### 6.3 `mini_app/src/hooks/useOrdQueries.ts` (NEW)

```typescript
export function useOrdStatus(placementRequestId: number | undefined) {
  return useQuery({
    queryKey: ['ord', placementRequestId],
    queryFn: () => ordApi.getStatus(placementRequestId!),
    enabled: !!placementRequestId,
    refetchInterval: (data) => data?.status === 'pending' ? 5000 : false,
  });
}

export function useRegisterOrd() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (placementRequestId: number) => ordApi.register(placementRequestId),
    onSuccess: (_, placementRequestId) => 
      qc.invalidateQueries({ queryKey: ['ord', placementRequestId] }),
  });
}
```

---

## 7. MINI APP — Screens

### 7.1 NEW Screens (7)

| Screen | File | Route | Purpose |
|--------|------|-------|---------|
| LegalProfilePrompt | `screens/common/LegalProfilePrompt.tsx` | `/legal-profile-prompt` | First-start prompt with skip option |
| LegalProfileSetup | `screens/common/LegalProfileSetup.tsx` | `/legal-profile` | Multi-step legal profile form |
| LegalProfileView | `screens/common/LegalProfileView.tsx` | `/legal-profile/view` | View/edit existing profile |
| ContractList | `screens/common/ContractList.tsx` | `/contracts` | List all user's contracts |
| ContractDetail | `screens/common/ContractDetail.tsx` | `/contracts/:id` | View + sign contract |
| AcceptRules | `screens/common/AcceptRules.tsx` | `/accept-rules` | Platform rules + privacy acceptance |
| CampaignVideo | `screens/advertiser/CampaignVideo.tsx` | `/campaign/video` | Optional video upload step |
| OrdStatus | `screens/advertiser/OrdStatus.tsx` | `/campaign/:id/ord` | ORD token status |

### 7.2 MODIFIED Screens (7)

| Screen | File | Changes |
|--------|------|---------|
| RoleSelect | `screens/common/RoleSelect.tsx` | After role chosen → navigate to LegalProfilePrompt (if not prompted yet) |
| Cabinet | `screens/common/Cabinet.tsx` | + "Юридический профиль" button, + "Мои договоры" button |
| CampaignText | `screens/advertiser/CampaignText.tsx` | + "Добавить видео" optional toggle → navigates to CampaignVideo |
| CampaignPayment | `screens/advertiser/CampaignPayment.tsx` | + contract generation + signing step before payment |
| CampaignPublished | `screens/advertiser/CampaignPublished.tsx` | + erid display, + ORD status badge |
| OwnPayoutRequest | `screens/owner/OwnPayoutRequest.tsx` | + tax info display based on legal status |
| MainMenu | `screens/common/MainMenu.tsx` | + legal profile completion banner if incomplete (dismissible) |

### 7.3 CRITICAL: First-Start Legal Profile Prompt

**Trigger:** User completes role selection (advertiser/owner/both) AND `legal_profile_prompted_at` is NULL.

**This is NOT a blocker** — user can always skip. But it MUST appear once.

#### 7.3.1 Bot flow (`/start` command):

```
/start
  → Welcome message
  → Role selection keyboard (advertiser / owner / both)
  → User picks role
  → IF user.legal_profile_prompted_at IS NULL:
      Bot sends:
        "📋 Для работы на платформе рекомендуем заполнить юридический профиль.
        
        Это нужно для:
        • Автоматического оформления договоров
        • Корректного расчёта налогов при выплатах
        • Маркировки рекламы (erid) по закону
        
        Вы можете заполнить реквизиты сейчас или позже в разделе «Кабинет»."
        
        [📝 Заполнить сейчас]    → callback: "legal:start"
        [⏭ Заполнить позже]      → callback: "legal:skip_first_start"
        
      → SET user.legal_profile_prompted_at = now()
      
      IF "Заполнить сейчас":
        → Enter LegalProfileStates.select_status (full legal profile wizard)
        → After completion OR cancel → redirect to role menu
        
      IF "Заполнить позже":
        → SET user.legal_profile_skipped_at = now()
        → Redirect to role menu immediately
        → Bot message: "Хорошо! Вы всегда можете заполнить профиль в разделе Кабинет → Юридический профиль"
  
  → ELSE (already prompted):
      → Redirect to role menu directly (normal flow)
```

#### 7.3.2 Mini App flow:

```
App launch → /auth → check user
  → IF user has no role → RoleSelect screen
  → IF user has role AND legal_profile_prompted_at IS NULL:
      → Navigate to LegalProfilePrompt screen (NEW)
  → ELSE:
      → Navigate to MainMenu

LegalProfilePrompt screen:
  - Info card explaining why legal profile matters
  - Two buttons:
    [📝 Заполнить сейчас] → navigate to /legal-profile
    [Позже]               → POST /api/users/skip-legal-prompt → navigate to MainMenu
  - Progress hint: "Шаг 2 из 2" (role was step 1)
```

#### 7.3.3 Subsequent reminders (non-blocking):

```
Reminder locations (soft nudges, NOT blocking):

1. MainMenu banner (dismissible):
   - Shows if legal_status_completed == false AND legal_profile_skipped_at is not null
   - "Заполните юридический профиль для работы с договорами"
   - [Заполнить] button
   - [✕] dismiss (hides for session, shows again next session)

2. Pre-action gates (BLOCKING only at action time):
   - Before first campaign payment → MUST have legal profile
   - Before first payout request → MUST have legal profile + signed contract
   - These show: "Для продолжения необходимо заполнить юридический профиль"
   - No skip option here — this is mandatory
```

#### 7.3.4 NEW API endpoint for skip:

| Method | Path | Handler | Request | Response | Notes |
|--------|------|---------|---------|----------|-------|
| POST | `/api/users/skip-legal-prompt` | `skip_legal_prompt` | — | `{success: true}` | Sets both prompted_at and skipped_at |

#### 7.3.5 NEW Mini App screen: LegalProfilePrompt

```
File: mini_app/src/screens/common/LegalProfilePrompt.tsx
Route: /legal-profile-prompt

Layout:
  ┌─────────────────────────────┐
  │      📋 (large icon)        │
  │                             │
  │  Заполните юридический      │
  │  профиль                    │
  │                             │
  │  Это нужно для:             │
  │  • Оформления договоров     │
  │  • Расчёта налогов          │
  │  • Маркировки рекламы       │
  │                             │
  │  ┌───────────────────────┐  │
  │  │  Заполнить сейчас  →  │  │
  │  └───────────────────────┘  │
  │                             │
  │     Заполнить позже         │
  │     (text button, muted)    │
  └─────────────────────────────┘

Uses: useSkipLegalPrompt() mutation
Navigation:
  "Заполнить сейчас" → navigate('/legal-profile')
  "Заполнить позже"  → mutate() then navigate('/menu')
```

### 7.4 Screen Flow: Legal Profile Setup

```
LegalProfileSetup (multi-step form inside one screen):

Step 1: "Выберите юридический статус"
  → 4 cards: ЮЛ / ИП / Самозанятый / Физлицо
  → useRequiredFields(selectedStatus) to get field list
  
Step 2: "Основные данные"
  → Dynamic form based on required fields
  → Fields: legal_name, inn (with inline validation), kpp, ogrn/ogrnip
  → tax_regime selector (only for ИП)
  
Step 3: "Платёжные реквизиты"  
  → IF legal_entity/ie: bank_name, bank_account, bank_bik, bank_corr_account
  → IF self_employed: yoomoney_wallet
  → IF individual: passport_series, passport_number, passport_issued_by, passport_issue_date
  
Step 4: "Документы"
  → Upload scans via Telegram (redirect to bot with deep link)
  → Shows checklist: ✅ Скан ИНН / ⬜ Скан паспорта / etc.
  
Step 5: "Подтверждение"
  → Summary of all entered data
  → "Сохранить" button → useCreateLegalProfile()
  
State management: campaignWizardStore pattern → new legalProfileStore (Zustand)
```

### 7.4 Screen Flow: Campaign with Video + Contract + ORD

```
EXISTING FLOW (extended):

CampaignCategory → CampaignFormat → CampaignChannels → CampaignText
                                                            ↓
                                                     [NEW] CampaignVideo (optional)
                                                            ↓
                                                     CampaignArbitration
                                                            ↓
                                                     [MODIFIED] CampaignPayment
                                                       ├── Generate advertiser_campaign contract
                                                       ├── Sign contract (button_accept)
                                                       ├── ORD registration (async, background)
                                                       └── Proceed to payment
                                                            ↓
                                                     CampaignWaiting
                                                            ↓
                                                     [MODIFIED] CampaignPublished
                                                       └── Shows erid + ORD status
```

### 7.5 Screen Flow: Owner First Payout

```
OwnPayoutRequest
  ├── IF !legal_status_completed → redirect to LegalProfileSetup
  ├── IF !owner_service contract signed → generate + sign contract
  ├── Show tax breakdown:
  │     ЮЛ:  "Сумма к выплате: {amount} ₽ (с НДС)"
  │     СМЗ: "Сумма к выплате: {amount} ₽ (НПД 6% вы платите самостоятельно)"
  │     Физ: "Сумма к выплате: {amount - 13%} ₽ (НДФЛ 13% удержан платформой)"
  └── Proceed with payout request
```

---

## 8. MINI APP — NEW Components (4)

### 8.1 `LegalStatusSelector`
```
Props: {
  value: LegalStatus | null;
  onChange: (status: LegalStatus) => void;
}
Location: mini_app/src/components/LegalStatusSelector.tsx
Renders: 4 cards with icon + title + description
```

### 8.2 `ContractCard`
```
Props: {
  contract: Contract;
  onSign?: () => void;
  onView?: () => void;
}
Location: mini_app/src/components/ContractCard.tsx
Renders: Card with type, status pill, dates, sign button
```

### 8.3 `TaxBreakdown`
```
Props: {
  grossAmount: number;
  legalStatus: LegalStatus;
  taxRegime?: TaxRegime;
}
Location: mini_app/src/components/TaxBreakdown.tsx
Renders: Breakdown of gross → tax → net amount
Computed:
  legal_entity: shows "с НДС 22%"
  self_employed: shows "НПД 6% — вы платите самостоятельно"
  individual: shows "НДФЛ 13% удержан: {tax}₽, к выплате: {net}₽"
```

### 8.4 `VideoUploader`
```
Props: {
  value: { fileId: string; url: string; duration: number } | null;
  onChange: (video: {...} | null) => void;
  maxDurationSeconds?: number;  // default 120
  maxSizeMb?: number;           // default 50
}
Location: mini_app/src/components/VideoUploader.tsx
Renders: Upload area, video preview, duration display, remove button
Note: Uses Telegram.WebApp.CloudStorage or deep link to bot for upload
```

---

## 9. MINI APP — Zustand Store

### 9.1 `mini_app/src/stores/legalProfileStore.ts` (NEW)

```typescript
interface LegalProfileState {
  currentStep: number;  // 0-4
  formData: Partial<LegalProfileCreate>;
  selectedStatus: LegalStatus | null;
  
  setStep: (step: number) => void;
  setSelectedStatus: (status: LegalStatus) => void;
  updateFormData: (data: Partial<LegalProfileCreate>) => void;
  reset: () => void;
}
```

### 9.2 Changes to `campaignWizardStore.ts`

```typescript
// Add to existing store:
interface CampaignWizardState {
  // ... existing fields ...
  mediaType: MediaType;              // NEW: 'none' | 'photo' | 'video'
  videoFileId: string | null;        // NEW
  videoUrl: string | null;           // NEW
  videoDuration: number | null;      // NEW
  videoThumbnailFileId: string | null; // NEW
  
  setVideo: (video: { fileId: string; url: string; duration: number; thumbnailFileId?: string } | null) => void;  // NEW
  setMediaType: (type: MediaType) => void;  // NEW
}
```

---

## 10. BOT — FSM States

### 10.1 `src/bot/states/legal_profile.py` (NEW)

```python
class LegalProfileStates(StatesGroup):
    select_status = State()           # Choose ЮЛ/ИП/СМЗ/Физ
    enter_legal_name = State()        # Наименование / ФИО
    enter_inn = State()               # ИНН
    enter_kpp = State()               # КПП (ЮЛ only)
    enter_ogrn = State()              # ОГРН/ОГРНИП
    select_tax_regime = State()       # ИП only
    enter_bank_name = State()         # Банк
    enter_bank_account = State()      # Р/С
    enter_bank_bik = State()          # БИК
    enter_yoomoney = State()          # Кошелёк (СМЗ only)
    enter_passport_series = State()   # Серия (Физ only)
    enter_passport_number = State()   # Номер (Физ only)
    enter_passport_issued = State()   # Кем выдан (Физ only)
    upload_scan = State()             # Upload document scan
    confirm = State()                 # Review & confirm
```

### 10.2 `src/bot/states/contract_signing.py` (NEW)

```python
class ContractSigningStates(StatesGroup):
    review = State()                  # View PDF, choose to sign
    enter_sms_code = State()          # If SMS method chosen
    complete = State()                # Confirmation
```

### 10.3 Changes to `src/bot/states/placement.py`

```python
class PlacementStates(StatesGroup):
    # ... existing states ...
    upload_video = State()            # NEW: optional video upload
    # existing: confirm, payment, etc.
```

---

## 11. BOT — Handlers

### 11.1 `src/bot/handlers/shared/legal_profile.py` (NEW)

```
Callbacks:
  "legal:start"                → start legal profile flow (from any context)
  "legal:skip_first_start"     → skip first-start prompt → set skipped_at → go to role menu
  "legal:status:{status}"      → select legal status (legal_entity|individual_entrepreneur|self_employed|individual)
  "legal:tax:{regime}"         → select tax regime
  "legal:skip"                 → skip mid-flow (from within wizard) → go to role menu
  "legal:confirm"              → save profile
  "legal:edit"                 → go back to edit
  "legal:scan:{type}"          → prompt scan upload

Message handlers:
  LegalProfileStates.enter_inn       → validate INN checksum
  LegalProfileStates.enter_legal_name → save name
  LegalProfileStates.enter_kpp      → validate KPP format
  ... (one per state)
  LegalProfileStates.upload_scan    → receive document/photo → save file_id
```

### 11.2 Changes to `src/bot/handlers/shared/start.py`

```
CURRENT flow:
  /start → welcome → role select → role menu

UPDATED flow:
  /start → welcome → role select → IF legal_profile_prompted_at IS NULL:
    → send legal profile prompt message with keyboard:
        [📝 Заполнить сейчас]   → "legal:start"
        [⏭ Заполнить позже]     → "legal:skip_first_start"
    → SET user.legal_profile_prompted_at = now()
  → ELSE:
    → role menu (unchanged)

IMPORTANT: start.py only adds the PROMPT after role selection.
The actual legal profile wizard lives in legal_profile.py handler.
start.py imports and calls show_legal_prompt() utility function.
```

### 11.3 `src/bot/handlers/shared/contract_signing.py` (NEW)

```
Callbacks:
  "contract:view:{id}"        → send PDF document to user
  "contract:sign:{id}"        → start signing flow
  "contract:accept_rules"     → accept platform rules + privacy
  
Message handlers:
  ContractSigningStates.enter_sms_code → verify code, mark signed
```

### 11.3 Changes to `src/bot/handlers/advertiser/campaigns.py`

```
NEW in campaign creation flow:
  After text step → "Добавить видео? (опционально)" inline button
  
Callbacks:
  "campaign:add_video"     → enter PlacementStates.upload_video
  "campaign:skip_video"    → proceed to arbitration
  
Message handlers:
  PlacementStates.upload_video → receive video message → save file_id + duration
  
NEW before payment:
  Auto-generate advertiser_campaign contract
  Show contract summary + "Подписать и оплатить" button
```

### 11.4 Changes to `src/bot/handlers/payout/payout.py`

```
NEW checks before payout:
  1. Check user.legal_status_completed → if not, redirect to legal:start
  2. Check owner_service contract exists + signed → if not, generate + prompt signing
  3. Show TaxBreakdown in payout confirmation message
```

---

## 12. BOT — Keyboards

### 12.1 `src/bot/keyboards/shared/legal_profile.py` (NEW)

```python
def legal_status_keyboard() -> InlineKeyboardMarkup:
    """4 buttons for legal status selection"""
    # "🏢 Юридическое лицо"        → callback: "legal:status:legal_entity"
    # "👤 Индивидуальный предприниматель" → "legal:status:individual_entrepreneur"
    # "📱 Самозанятый"              → "legal:status:self_employed"
    # "🙋 Физическое лицо"          → "legal:status:individual"
    # "⏭ Заполнить позже"           → "legal:skip"

def first_start_legal_prompt_keyboard() -> InlineKeyboardMarkup:
    """First-start prompt: fill now or skip"""
    # "📝 Заполнить сейчас"  → callback: "legal:start"
    # "⏭ Заполнить позже"    → callback: "legal:skip_first_start"

def tax_regime_keyboard() -> InlineKeyboardMarkup:
    """Tax regime selection for ИП"""
    # "ОСНО"  → "legal:tax:osno"
    # "УСН доходы" → "legal:tax:usn_d"
    # "УСН доходы-расходы" → "legal:tax:usn_dr"
    # "Патент" → "legal:tax:patent"

def scan_upload_keyboard(legal_status: LegalStatus, uploaded: dict[str, bool]) -> InlineKeyboardMarkup:
    """Dynamic keyboard showing which scans are needed/uploaded"""
    # "✅ Скан ИНН" or "📎 Загрузить скан ИНН" → "legal:scan:inn"
    # "📎 Загрузить скан паспорта" → "legal:scan:passport"  (individual only)
    # etc.
    # "✅ Готово" → "legal:confirm" (only if all required uploaded)

def legal_profile_confirm_keyboard() -> InlineKeyboardMarkup:
    # "✅ Подтвердить" → "legal:confirm"
    # "✏️ Редактировать" → "legal:edit"
```

### 12.2 `src/bot/keyboards/shared/contract.py` (NEW)

```python
def contract_sign_keyboard(contract_id: int) -> InlineKeyboardMarkup:
    # "📄 Посмотреть договор" → "contract:view:{contract_id}"
    # "✍️ Подписать"          → "contract:sign:{contract_id}"

def accept_rules_keyboard() -> InlineKeyboardMarkup:
    # "📄 Правила платформы"             → deep link to rules page
    # "🔒 Политика конфиденциальности"  → deep link to privacy page
    # "✅ Принимаю правила и политику"   → "contract:accept_rules"
```

### 12.3 Changes to campaign keyboards

```python
# In src/bot/keyboards/advertiser/placement.py:

def video_upload_keyboard() -> InlineKeyboardMarkup:
    # "🎬 Загрузить видео"    → "campaign:add_video"
    # "⏭ Пропустить"          → "campaign:skip_video"

def video_confirm_keyboard() -> InlineKeyboardMarkup:
    # "✅ Видео загружено"     → "campaign:video_confirm"
    # "🔄 Загрузить другое"   → "campaign:add_video"
    # "❌ Удалить видео"       → "campaign:remove_video"
```

---

## 13. CORE SERVICES

### 13.1 `src/core/services/contract_service.py` (NEW)

```python
class ContractService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ContractRepo(session)
        self.legal_repo = LegalProfileRepo(session)

    async def generate_contract(
        self,
        user_id: int,
        contract_type: ContractType,
        placement_request_id: int | None = None,
    ) -> Contract:
        """Generate PDF contract based on user's legal profile"""

    async def sign_contract(
        self,
        contract_id: int,
        user_id: int,
        method: SignatureMethod,
        sms_code: str | None = None,
        ip_address: str | None = None,
    ) -> Contract:
        """Sign contract with simple electronic signature"""

    async def accept_platform_rules(
        self,
        user_id: int,
    ) -> None:
        """Accept platform rules + privacy policy"""

    async def get_user_contracts(
        self,
        user_id: int,
        contract_type: ContractType | None = None,
    ) -> list[Contract]:
        """List user's contracts"""

    async def check_owner_contract(self, user_id: int) -> bool:
        """Check if owner has signed service contract"""

    async def check_advertiser_can_pay(
        self, user_id: int, placement_request_id: int
    ) -> tuple[bool, Contract | None]:
        """Check if campaign contract exists, generate if needed"""

    def _render_template(
        self, contract_type: ContractType, legal_profile: LegalProfile
    ) -> str:
        """Render Jinja2 template → HTML string"""

    def _html_to_pdf(self, html: str) -> bytes:
        """Convert HTML → PDF bytes via WeasyPrint"""
```

### 13.2 `src/core/services/ord_service.py` (NEW)

```python
class OrdService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OrdRegistrationRepo(session)

    async def register_advertiser(self, user_id: int) -> str:
        """Register advertiser in ORD system → return ord_advertiser_id"""

    async def register_creative(
        self, placement_request_id: int, ad_text: str, media_type: MediaType
    ) -> OrdRegistration:
        """Register ad creative → get ord_creative_id"""

    async def get_erid(self, placement_request_id: int) -> str | None:
        """Get advertising token (erid) for marking"""

    async def report_publication(
        self,
        placement_request_id: int,
        channel_id: int,
        published_at: datetime,
        post_url: str,
    ) -> None:
        """Report actual publication to ORD"""

    async def get_status(self, placement_request_id: int) -> OrdRegistration | None:
        """Get current ORD registration status"""
```

### 13.3 `src/core/services/legal_profile_service.py` (NEW)

```python
class LegalProfileService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LegalProfileRepo(session)

    async def create_profile(
        self, user_id: int, data: LegalProfileCreate
    ) -> LegalProfile:
        """Create legal profile, auto-set tax_regime for self_employed/individual"""

    async def update_profile(
        self, user_id: int, data: LegalProfileUpdate
    ) -> LegalProfile:
        """Partial update"""

    async def upload_scan(
        self, user_id: int, scan_type: str, file_id: str
    ) -> None:
        """Save Telegram file_id for document scan"""

    async def get_required_fields(
        self, legal_status: LegalStatus
    ) -> RequiredFields:
        """Return list of required fields for given status"""

    async def check_completeness(self, user_id: int) -> bool:
        """Check if all required fields are filled, update user flag"""

    @staticmethod
    def validate_inn(inn: str) -> tuple[bool, str]:
        """Validate INN checksum, return (valid, type: '10-digit'|'12-digit')"""

    async def calculate_tax(
        self, user_id: int, gross_amount: Decimal
    ) -> TaxCalculation:
        """Calculate tax based on legal status"""
```

### 13.4 Changes to `src/core/services/publication_service.py`

```python
# In publish() method, BEFORE sending to Telegram:

# 1. Get erid from OrdRegistration
erid = await self.ord_service.get_erid(placement.id)

# 2. Append ad marking to text
if erid:
    marked_text = f"{placement.ad_text}\n\nРеклама. {advertiser_legal_name}\nerid: {erid}"
else:
    marked_text = placement.ad_text

# 3. Send based on media_type
if placement.media_type == MediaType.video:
    await bot.send_video(
        chat_id=channel_id,
        video=placement.video_file_id,
        caption=marked_text,
        parse_mode="HTML",
    )
elif placement.media_type == MediaType.photo:
    await bot.send_photo(
        chat_id=channel_id,
        photo=placement.image_file_id,
        caption=marked_text,
        parse_mode="HTML",
    )
else:
    await bot.send_message(
        chat_id=channel_id,
        text=marked_text,
        parse_mode="HTML",
    )

# 4. Report to ORD
await self.ord_service.report_publication(
    placement_request_id=placement.id,
    channel_id=channel_id,
    published_at=datetime.utcnow(),
    post_url=post_url,
)
```

### 13.5 Changes to `src/core/services/payout_service.py`

```python
# Add tax calculation before payout:

async def calculate_payout_with_tax(
    self, user_id: int, gross_amount: Decimal
) -> PayoutCalculation:
    profile = await self.legal_service.get_profile(user_id)
    
    if not profile:
        raise ValueError("Legal profile required for payout")
    
    if profile.legal_status == LegalStatus.legal_entity:
        # Platform pays VAT separately, owner gets full amount
        return PayoutCalculation(
            gross=gross_amount, tax=Decimal(0), net=gross_amount,
            tax_note="Сумма с НДС. НДС уплачивается платформой."
        )
    elif profile.legal_status == LegalStatus.individual_entrepreneur:
        # Same as ЮЛ for payout purposes
        return PayoutCalculation(
            gross=gross_amount, tax=Decimal(0), net=gross_amount,
            tax_note="Налог уплачивается вами самостоятельно по выбранному режиму."
        )
    elif profile.legal_status == LegalStatus.self_employed:
        # Self-employed pays NPD themselves
        return PayoutCalculation(
            gross=gross_amount, tax=Decimal(0), net=gross_amount,
            tax_note="НПД (6%) вы уплачиваете самостоятельно."
        )
    elif profile.legal_status == LegalStatus.individual:
        # Platform withholds NDFL 13%
        ndfl = (gross_amount * Decimal("0.13")).quantize(Decimal("0.01"))
        return PayoutCalculation(
            gross=gross_amount, tax=ndfl, net=gross_amount - ndfl,
            tax_note=f"НДФЛ 13% ({ndfl} ₽) удержан платформой."
        )
```

---

## 14. REPOSITORIES (NEW)

### 14.1 `src/db/repositories/legal_profile_repo.py`

```python
class LegalProfileRepo(BaseRepository[LegalProfile]):
    model = LegalProfile

    async def get_by_user_id(self, user_id: int) -> LegalProfile | None
    async def create(self, user_id: int, **kwargs) -> LegalProfile
    async def update(self, user_id: int, **kwargs) -> LegalProfile
    async def update_scan(self, user_id: int, scan_field: str, file_id: str) -> None
```

### 14.2 `src/db/repositories/contract_repo.py`

```python
class ContractRepo(BaseRepository[Contract]):
    model = Contract

    async def get_by_user_and_type(
        self, user_id: int, contract_type: ContractType
    ) -> Contract | None
    
    async def get_by_user_and_placement(
        self, user_id: int, placement_request_id: int
    ) -> Contract | None
    
    async def list_by_user(
        self, user_id: int, contract_type: ContractType | None = None
    ) -> list[Contract]
    
    async def mark_signed(
        self, contract_id: int, method: SignatureMethod, ip: str | None
    ) -> Contract
```

### 14.3 `src/db/repositories/ord_registration_repo.py`

```python
class OrdRegistrationRepo(BaseRepository[OrdRegistration]):
    model = OrdRegistration

    async def get_by_placement(self, placement_request_id: int) -> OrdRegistration | None
    async def update_status(self, id: int, status: OrdStatus, **kwargs) -> OrdRegistration
    async def get_erid(self, placement_request_id: int) -> str | None
```

---

## 15. CELERY TASKS

### 15.1 `src/tasks/contract_tasks.py` (NEW)

```python
@celery_app.task(queue="critical")
def generate_contract_pdf(contract_id: int) -> None:
    """Background PDF generation for heavy templates"""

@celery_app.task(queue="critical")  
def send_contract_notification(user_id: int, contract_id: int) -> None:
    """Notify user that contract is ready for signing"""
```

### 15.2 `src/tasks/ord_tasks.py` (NEW)

```python
@celery_app.task(queue="critical")
def register_creative_in_ord(placement_request_id: int) -> None:
    """Register creative in ORD and get erid token"""
    # 1. Get placement details
    # 2. Call ORD API to register creative
    # 3. Get erid token
    # 4. Save to ord_registrations table
    # 5. Copy erid to placement_requests.erid
    # Retry on failure: max 3 times with exponential backoff

@celery_app.task(queue="background")
def report_publication_to_ord(placement_request_id: int, post_url: str) -> None:
    """Report actual publication to ORD after post goes live"""

@celery_app.task(queue="background")
def verify_self_employed_status(user_id: int) -> None:
    """Verify self-employed status via FNS API"""
    # Called after user claims self_employed status
    # Updates is_verified flag
```

### 15.3 Changes to existing tasks

```python
# src/tasks/publication_tasks.py — add video support:
# When publishing, check media_type and send appropriate message type

# src/tasks/placement_tasks.py — add ORD trigger:
# After placement moves to 'escrow' status → trigger register_creative_in_ord
```

---

## 16. ALEMBIC MIGRATION

### Migration: `add_legal_profiles_contracts_ord_video`

```python
"""Add legal_profiles, contracts, ord_registrations tables; video support in placement_requests"""

def upgrade():
    # 1. Create legal_profiles table
    # 2. Create contracts table  
    # 3. Create ord_registrations table
    # 4. Add columns to users: legal_status_completed, legal_profile_prompted_at, legal_profile_skipped_at, platform_rules_accepted_at, privacy_policy_accepted_at
    # 5. Add columns to placement_requests: media_type, video_file_id, video_url, video_thumbnail_file_id, video_duration, erid
    # 6. Create indexes

def downgrade():
    # Reverse all above
```

---

## 17. VIDEO SUPPORT — Detailed Flow

### 17.1 Constraints

```
MAX_VIDEO_DURATION = 120        # seconds (Telegram limit for inline video)
MAX_VIDEO_SIZE_MB = 50          # MB
ALLOWED_VIDEO_FORMATS = ["mp4", "mov", "avi"]  # Telegram accepts most
THUMBNAIL_AUTO_GENERATED = True  # Telegram generates thumbnail
```

### 17.2 Bot Flow

```
Campaign wizard, after CampaignText step:

Bot: "Хотите добавить видео к рекламному посту? (опционально)"
  [🎬 Добавить видео]  [⏭ Пропустить]

IF user clicks "Добавить видео":
  Bot: "Отправьте видеофайл (до 2 минут, до 50 МБ)"
  → PlacementStates.upload_video
  
  User sends video message → handler extracts:
    - message.video.file_id → video_file_id
    - message.video.duration → video_duration  
    - message.video.thumbnail.file_id → video_thumbnail_file_id (if present)
    - message.video.file_size → validate size
  
  IF duration > 120: "Видео слишком длинное. Максимум 2 минуты."
  IF file_size > 50MB: "Файл слишком большой. Максимум 50 МБ."
  
  Bot: "✅ Видео загружено ({duration}с)"
  [✅ Продолжить]  [🔄 Заменить]  [❌ Удалить]
```

### 17.3 Mini App Flow

```
CampaignText screen:
  Bottom of screen: Toggle "Добавить видео"
  
IF toggled ON → navigate to CampaignVideo screen:
  - VideoUploader component
  - "Upload via bot" deep link (tg://resolve?domain=RekHarborBot&start=upload_video_{session_id})
  - Preview area with thumbnail
  - Duration display
  - "Далее" button → saves to campaignWizardStore, returns to flow

CampaignVideo → back to CampaignArbitration (or wherever next step is)
```

### 17.4 Publication Logic

```python
# In PublicationService.publish():

if placement.media_type == MediaType.video:
    result = await bot.send_video(
        chat_id=channel_chat_id,
        video=placement.video_file_id,
        caption=marked_text,           # includes erid marking
        parse_mode="HTML",
        duration=placement.video_duration,
    )
elif placement.media_type == MediaType.photo:
    result = await bot.send_photo(...)
else:
    result = await bot.send_message(...)
```

---

## 18. CONSTANTS

### 18.1 `src/constants/legal.py` — additions

```python
# Tax rates (VERIFIED 2026-03-22)
# ФЗ от 28.11.2025 № 425-ФЗ — НДС повышен с 20% до 22% с 01.01.2026
VAT_RATE = Decimal("0.22")           # 22% НДС (с 01.01.2026, ранее 20%)
NDFL_RATE = Decimal("0.13")          # 13% НДФЛ (базовая ставка, до 2.4 млн/год)
# Прогрессивная шкала НДФЛ 2026: 13% до 2.4М, 15% до 5М, 18% до 20М, 20% до 50М, 22% свыше 50М
# Для платформы релевантна ставка 13% — владельцы каналов вряд ли превысят 2.4М через платформу
NPD_RATE_FROM_LEGAL = Decimal("0.06") # 6% НПД (от юрлиц/ИП) — без изменений в 2026
NPD_RATE_FROM_INDIVIDUAL = Decimal("0.04") # 4% НПД (от физлиц) — без изменений в 2026
# НПД действует до 31.12.2028, лимит 2.4 млн руб/год

# УСН: с 2026 порог НДС снижен до 20 млн руб (было 60 млн)
# Спецставки для УСН: 5% (доходы до 272.5М), 7% (доходы до 490.5М)

# Video constraints  
MAX_VIDEO_DURATION_SECONDS = 120
MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# Contract template versions
CONTRACT_TEMPLATE_VERSION = "1.0"

# INN validation
INN_WEIGHTS_10 = [2, 4, 10, 3, 5, 9, 4, 6, 8]
INN_WEIGHTS_12_1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
INN_WEIGHTS_12_2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
```

---

## 19. ЭДО INTEGRATION (Electronic Document Interchange)

### 19.1 Overview

ЭДО обязателен для работы с юридическими лицами и ИП — они нуждаются в УПД (универсальный передаточный документ), счетах-фактурах и актах для бухгалтерского учёта. Самозанятые и физлица ЭДО не используют.

**Когда нужен ЭДО:**
- ЮЛ/ИП оплачивает рекламную кампанию → платформа формирует УПД и отправляет через ЭДО
- Владелец канала (ЮЛ/ИП) получает выплату → платформа формирует акт выполненных работ через ЭДО
- Закрытие отчётного периода → сверка через ЭДО

**Когда НЕ нужен:**
- Самозанятый — чек формирует сам через "Мой налог", платформа может получить чек через API ФНС
- Физлицо — платформа как налоговый агент удерживает НДФЛ, ЭДО не требуется

### 19.2 Provider Selection

Два основных оператора ЭДО в России:

| Оператор | API | Роуминг | Подпись | Стоимость |
|----------|-----|---------|---------|-----------|
| Контур.Диадок | REST API (HTTP-based) | Да (СБИС, Такском, СберКорус и др.) | КЭП | от ~6₽/документ |
| СБИС (Saby/Тензор) | REST API (JSON-RPC стиль) | Да (Диадок, Такском и др.) | КЭП | от ~5₽/документ |

**Рекомендация:** Контур.Диадок — более зрелый API, лучшая документация, больше интеграций. СБИС — альтернатива. Благодаря роумингу контрагент может использовать любого оператора.

**Для MVP:** начать с одного оператора (Диадок), абстрагировать через интерфейс `EdoProvider`.

### 19.3 Architecture: `EdoService`

```python
class EdoProvider(Protocol):
    """Abstract EDO provider interface — swap Diadoc/SBIS without code changes"""
    
    async def authenticate(self) -> str:
        """Get session token"""
    
    async def send_upd(
        self, 
        sender_inn: str,
        receiver_inn: str, 
        upd_xml: bytes,
        signature: bytes,
    ) -> str:
        """Send UPD to counterparty → return document_id"""
    
    async def send_act(
        self, 
        sender_inn: str,
        receiver_inn: str,
        act_xml: bytes,
        signature: bytes,
    ) -> str:
        """Send act of completed works → return document_id"""
    
    async def get_document_status(self, document_id: str) -> EdoDocumentStatus:
        """Check if document was received/signed/rejected"""
    
    async def find_counterparty(self, inn: str) -> EdoCounterparty | None:
        """Check if counterparty is registered in EDO"""


class DiadocProvider(EdoProvider):
    """Контур.Диадок implementation"""
    BASE_URL = "https://diadoc-api.kontur.ru"
    
    # Auth: POST /Authenticate with login/password or certificate
    # Send UPD: POST /V3/PostMessage with DocumentAttachment type=UniversalTransferDocument
    # Status: GET /V4/GetMessage
    # Find: GET /GetOrganizationsByInnList


class EdoService:
    def __init__(self, session: AsyncSession, provider: EdoProvider):
        self.session = session
        self.provider = provider
        self.repo = EdoDocumentRepo(session)
    
    async def send_upd_for_payment(
        self, placement_request_id: int
    ) -> EdoDocument:
        """Generate and send UPD when advertiser (ЮЛ/ИП) pays for campaign"""
        # 1. Get placement + advertiser's legal profile
        # 2. Check legal_status is legal_entity or individual_entrepreneur
        # 3. Generate UPD XML (format per ФНС Приказ ММВ-7-15/820@)
        # 4. Sign with platform's КЭП
        # 5. Send via provider
        # 6. Save EdoDocument record
    
    async def send_act_for_payout(
        self, payout_id: int
    ) -> EdoDocument:
        """Generate and send act when owner (ЮЛ/ИП) receives payout"""
        # Same flow but with act of completed works
    
    async def check_counterparty_edo(
        self, inn: str
    ) -> bool:
        """Check if counterparty is registered in any EDO operator"""
```

### 19.4 New DB Model: `edo_documents` table

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| id | SERIAL | NO | auto | PK |
| user_id | BIGINT | NO | — | FK→users.id |
| document_type | VARCHAR(30) | NO | — | 'upd', 'act', 'invoice' |
| direction | VARCHAR(10) | NO | — | 'outgoing', 'incoming' |
| placement_request_id | INTEGER | YES | NULL | FK→placement_requests.id |
| payout_id | INTEGER | YES | NULL | FK→payouts.id |
| provider | VARCHAR(30) | NO | "diadoc" | EDO operator |
| external_document_id | VARCHAR(200) | YES | NULL | ID in EDO system |
| status | VARCHAR(20) | NO | "draft" | draft/sent/delivered/signed/rejected |
| counterparty_inn | VARCHAR(12) | YES | NULL | |
| xml_content | TEXT | YES | NULL | stored UPD/act XML |
| error_message | TEXT | YES | NULL | |
| sent_at | TIMESTAMP | YES | NULL | |
| signed_at | TIMESTAMP | YES | NULL | counterparty signed |
| created_at | TIMESTAMP | NO | now() | |

### 19.5 EDO Document Flow

```
Advertiser (ЮЛ/ИП) pays for campaign:
  1. Payment confirmed in YooKassa
  2. Celery task: generate_upd_task(placement_request_id)
  3. EdoService.send_upd_for_payment()
     - Generates UPD XML with:
       - Seller: Platform (our ИНН, КПП)
       - Buyer: Advertiser (their ИНН from LegalProfile)
       - Service: "Размещение рекламного материала в Telegram-канале"
       - Amount: payment amount
       - НДС: 22% (VAT_RATE)
       - Date: payment date
     - Signs with platform КЭП
     - Sends to advertiser via Diadoc API
  4. Save EdoDocument with status='sent'
  5. Celery periodic task: check_edo_statuses()
     - Polls Diadoc for status updates
     - Updates EdoDocument when counterparty signs/rejects

Owner (ЮЛ/ИП) receives payout:
  1. Payout processed
  2. Celery task: generate_act_task(payout_id)
  3. EdoService.send_act_for_payout()
     - Generates Act of completed works
     - Signs and sends
  4. Save EdoDocument
```

### 19.6 Requirements for КЭП (Qualified Electronic Signature)

**Platform needs:**
- КЭП certificate for the platform's legal entity (issued by accredited CA)
- Certificate stored on server (hardware HSM recommended, software token for MVP)
- Library: `cryptopro` or `pycades` for signing XML with ГОСТ algorithms
- Alternative: cloud КЭП service (Контур.Подпись, КриптоПро DSS)

**Counterparty needs:**
- Their own КЭП for signing incoming documents
- This is their responsibility — they sign in their EDO web interface (Diadoc/SBIS)

### 19.7 When to implement EDO

**Phase E2 (after MVP launch):**
EDO is important but not blocking for launch. For MVP:
- Generate PDF versions of УПД/acts locally
- Send PDF via bot/email to ЮЛ/ИП clients  
- Manual ЭДО exchange (client enters into their system themselves)

**Phase E3 (post-launch):**
- Full Diadoc API integration
- Automated UPD/act generation and sending
- Status tracking in admin panel
- КЭП integration

### 19.8 Files for EDO (deferred to Phase E2/E3)

```
NEW (Phase E2/E3):
  src/core/services/edo_service.py           # Main EDO service
  src/core/services/edo_providers/diadoc.py  # Diadoc implementation
  src/core/services/edo_providers/base.py    # Protocol/interface
  src/db/models/edo_document.py              # EdoDocument model
  src/db/repositories/edo_document_repo.py   # Repository
  src/tasks/edo_tasks.py                     # Celery: generate, check status
  src/api/routers/edo.py                     # API for Mini App
  src/api/schemas/edo.py                     # Schemas
  src/utils/upd_generator.py                 # UPD XML builder
  mini_app/src/api/edo.ts                    # API client
  mini_app/src/hooks/useEdoQueries.ts        # Hooks
  mini_app/src/screens/common/EdoDocuments.tsx # Screen
```

### 19.9 Enum: EdoDocumentStatus

```
DB column type:   VARCHAR(20)
Python enum name: EdoDocumentStatus
TS type name:     EdoDocumentStatus

Values:
  "draft"       → UI: "Черновик"
  "sent"        → UI: "Отправлен"
  "delivered"   → UI: "Доставлен"
  "signed"      → UI: "Подписан контрагентом"
  "rejected"    → UI: "Отклонён"
  "error"       → UI: "Ошибка отправки"
```

---

## 20. FILE CREATION CHECKLIST

### New files to create (27 total):

```
MODELS (3):
  src/db/models/legal_profile.py
  src/db/models/contract.py
  src/db/models/ord_registration.py

REPOSITORIES (3):
  src/db/repositories/legal_profile_repo.py
  src/db/repositories/contract_repo.py
  src/db/repositories/ord_registration_repo.py

SERVICES (3):
  src/core/services/legal_profile_service.py
  src/core/services/contract_service.py
  src/core/services/ord_service.py

API (4):
  src/api/routers/legal_profile.py
  src/api/routers/contracts.py
  src/api/routers/ord.py
  src/api/schemas/legal_profile.py    # includes contract + ord schemas

BOT (6):
  src/bot/states/legal_profile.py
  src/bot/states/contract_signing.py
  src/bot/handlers/shared/legal_profile.py
  src/bot/handlers/shared/contract_signing.py
  src/bot/keyboards/shared/legal_profile.py
  src/bot/keyboards/shared/contract.py

TASKS (2):
  src/tasks/contract_tasks.py
  src/tasks/ord_tasks.py

TEMPLATES (6):
  src/templates/contracts/owner_service_legal_entity.html
  src/templates/contracts/owner_service_ie.html
  src/templates/contracts/owner_service_self_employed.html
  src/templates/contracts/owner_service_individual.html
  src/templates/contracts/advertiser_campaign.html
  src/templates/contracts/platform_rules.html

MINI APP (14):
  mini_app/src/api/legalProfile.ts
  mini_app/src/api/contracts.ts
  mini_app/src/api/ord.ts
  mini_app/src/hooks/useLegalProfileQueries.ts
  mini_app/src/hooks/useContractQueries.ts
  mini_app/src/hooks/useOrdQueries.ts
  mini_app/src/stores/legalProfileStore.ts
  mini_app/src/screens/common/LegalProfilePrompt.tsx
  mini_app/src/screens/common/LegalProfileSetup.tsx
  mini_app/src/screens/common/LegalProfileView.tsx
  mini_app/src/screens/common/ContractList.tsx
  mini_app/src/screens/common/ContractDetail.tsx
  mini_app/src/screens/common/AcceptRules.tsx
  mini_app/src/screens/advertiser/CampaignVideo.tsx
  mini_app/src/components/LegalStatusSelector.tsx
  mini_app/src/components/ContractCard.tsx
  mini_app/src/components/TaxBreakdown.tsx
  mini_app/src/components/VideoUploader.tsx

MIGRATION (1):
  src/db/migrations/versions/xxx_add_legal_contracts_ord_video.py
```

### Files to modify (12 total):

```
MODELS:
  src/db/models/user.py                    # +3 columns
  src/db/models/placement_request.py       # +6 columns (video + erid)
  src/db/models/__init__.py                # register new models

SERVICES:
  src/core/services/publication_service.py  # video + erid marking
  src/core/services/payout_service.py       # tax-aware calculation

BOT:
  src/bot/states/placement.py               # +upload_video state
  src/bot/handlers/shared/start.py          # +legal profile prompt after role select
  src/bot/handlers/advertiser/campaigns.py  # video step + contract step
  src/bot/handlers/payout/payout.py         # legal profile check

API:
  src/api/schemas/placement.py              # +media_type, video_*, erid
  src/api/routers/users.py                  # +legal fields in /me response
  src/api/main.py                           # register new routers

MINI APP:
  mini_app/src/lib/types.ts                 # all new types
  mini_app/src/stores/campaignWizardStore.ts # +video fields
  mini_app/src/screens/common/RoleSelect.tsx # redirect to LegalProfilePrompt
  mini_app/src/screens/common/Cabinet.tsx   # +legal profile link
  mini_app/src/screens/advertiser/CampaignText.tsx      # +video toggle
  mini_app/src/screens/advertiser/CampaignPayment.tsx   # +contract step
  mini_app/src/screens/advertiser/CampaignPublished.tsx # +erid display
  mini_app/src/screens/owner/OwnPayoutRequest.tsx       # +tax breakdown
  mini_app/src/screens/common/MainMenu.tsx              # +completion banner
```

### Files to NEVER touch:
```
  src/core/services/xp_service.py
  src/core/services/user_role_service.py
  src/core/services/badge_service.py
  src/bot/states/campaign_create.py
```

---

## 21. NAMING CONVENTIONS SUMMARY

| Layer | Convention | Example |
|-------|-----------|---------|
| DB column | snake_case | `legal_status`, `video_file_id` |
| DB table | snake_case plural | `legal_profiles`, `contracts` |
| Python enum | PascalCase class, snake_case values | `LegalStatus.self_employed` |
| Pydantic field | snake_case | `legal_name: str` |
| API path | kebab-case | `/api/legal-profile/me` |
| API query param | snake_case | `?legal_status=self_employed` |
| TS type | PascalCase | `LegalProfile`, `ContractType` |
| TS field | snake_case (matches API) | `legal_status`, `video_file_id` |
| TS API function | camelCase | `getMyProfile()`, `createProfile()` |
| TS hook | camelCase with use prefix | `useMyLegalProfile()` |
| TS store | camelCase | `legalProfileStore` |
| React component | PascalCase | `LegalStatusSelector` |
| Screen file | PascalCase.tsx | `LegalProfileSetup.tsx` |
| Bot callback_data | colon-separated | `legal:status:self_employed` |
| Bot state | PascalCase.snake_case | `LegalProfileStates.enter_inn` |
| Celery task | snake_case | `register_creative_in_ord` |
| Template file | snake_case.html | `owner_service_legal_entity.html` |

---

*End of spec. This document is the single source of truth. Any implementation that deviates from field names, paths, or type names defined here is a bug.*
