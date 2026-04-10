"""Schemas for legal profile, contracts, and ORD registration."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict


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


class ContractType(str, Enum):
    owner_service = "owner_service"
    advertiser_campaign = "advertiser_campaign"
    advertiser_framework = "advertiser_framework"
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


class OrdStatus(str, Enum):
    pending = "pending"
    registered = "registered"
    token_received = "token_received"  # nosec B105 — enum value, not a password
    reported = "reported"
    failed = "failed"


class MediaType(str, Enum):
    none = "none"
    photo = "photo"
    video = "video"


# ─── Request Schemas ────────────────────────────────────────────


class LegalProfileCreate(BaseModel):
    legal_status: LegalStatus
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


class LegalProfileUpdate(BaseModel):
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
    file_id: str


class ContractSignRequest(BaseModel):
    signature_method: SignatureMethod
    sms_code: str | None = None


class AcceptRulesRequest(BaseModel):
    accept_platform_rules: bool
    accept_privacy_policy: bool


class GenerateContractRequest(BaseModel):
    contract_type: ContractType
    placement_request_id: int | None = None


class ValidateInnRequest(BaseModel):
    inn: str


class RegisterOrdRequest(BaseModel):
    placement_request_id: int


# ─── Response Schemas ───────────────────────────────────────────


class LegalProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    legal_status: LegalStatus
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
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    # Computed flags — populated by router
    has_passport_data: bool = False
    has_inn_scan: bool = False
    has_passport_scan: bool = False
    has_self_employed_cert: bool = False
    has_company_doc: bool = False
    is_complete: bool = False


class RequiredFieldsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fields: list[str]
    scans: list[str]
    show_bank_details: bool
    show_passport: bool
    show_yoomoney: bool
    tax_regime_required: bool


class KepRequestBody(BaseModel):
    contract_id: int
    email: str


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    contract_type: ContractType
    contract_status: ContractStatus
    placement_request_id: int | None = None
    template_version: str
    signature_method: SignatureMethod | None = None
    signed_at: datetime | None = None
    expires_at: datetime | None = None
    pdf_url: str | None = None
    kep_requested: bool = False
    kep_request_email: str | None = None
    role: str | None = None
    created_at: datetime
    updated_at: datetime


class ContractListResponse(BaseModel):
    items: list[ContractResponse]
    total: int


class OrdRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    placement_request_id: int
    erid: str | None = None
    status: OrdStatus
    ord_provider: str
    error_message: str | None = None
    created_at: datetime


class ValidateInnResponse(BaseModel):
    valid: bool
    type: str


class FnsValidationError(BaseModel):
    field: str
    message: str


class FnsValidationResponse(BaseModel):
    """Результат валидации через ФНС (контрольные суммы ИНН/ОГРН)."""

    is_valid: bool
    entity_type: str | None = None  # 'legal_entity', 'individual_entrepreneur', 'individual'
    inn: str | None = None
    name: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    status: str | None = None
    errors: list[FnsValidationError] = []
    warnings: list[str] = []


class ValidateEntityRequest(BaseModel):
    """Запрос на валидацию юрлица или ИП."""

    inn: str
    legal_status: str  # needed to cross-validate INN type vs selected status
    legal_name: str | None = None
    kpp: str | None = None
    ogrn: str | None = None
    ogrnip: str | None = None
    passport_series: str | None = None
    passport_number: str | None = None
