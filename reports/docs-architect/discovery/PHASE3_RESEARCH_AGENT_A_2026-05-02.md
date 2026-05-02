# Phase 3 Research — Agent A: LegalProfile Current Structure Audit
**Generated:** 2026-05-02  
**Research Agent:** A — legal_profile structure audit  
**Branch:** `develop` HEAD 7ae137c  
**Scope:** Empirical audit of LegalProfile model, schemas, services, repositories, and frontend patterns.

---

## Executive Summary

**Current state:** LegalProfile model contains 23 fields across ORM + migration; uses terminology `legal_status` (not `legal_type` as plan mentions). Four legal statuses: `individual`, `individual_entrepreneur`, `self_employed`, `legal_entity`. 

**Gap findings:**
- **MISSING (per Phase 3 §3.B.7):** Four fields required for gate-checker compliance: `fns_verification_status`, `fns_verified_at`, `egrul_snapshot_at`, `inn_checksum_valid`. These fields are **not present** in model, schema, migration, or service logic.
- **Terminology mismatch:** Plan consistently uses term `legal_type`; codebase uses `legal_status`. No enum called `legal_type` exists anywhere.
- **Mini_app compliance ✓:** LegalProfileView correctly redirects to web_portal (ФЗ-152 compliance — no PII in mini_app).
- **Field encryption ✓:** PII fields (INN, passport, bank details) correctly encrypted at rest per 16.x series; INN indexed via HMAC hash.
- **Audit integration:** Service mutations (create_profile, update_profile) do NOT log to audit_log. No mutation tracking exists for compliance-critical field changes.

**Required action:** Add 4 fields to `0001_initial_schema.py` migration + schema + service. Ensure backward compatibility (all new fields default NULL/unchecked initially).

---

## Findings

### 1. LegalProfile ORM Model — All Fields

**File:** `src/db/models/legal_profile.py`  
**Lines:** 16–67

| Field | Type | Nullable | Encrypted | Indexed | Notes |
|-------|------|----------|-----------|---------|-------|
| `id` | Integer | NO | — | PK | autoincrement |
| `user_id` | Integer | NO | — | Unique FK | One profile per user |
| `legal_status` | String(30) | NO | — | — | Enum values: individual, individual_entrepreneur, self_employed, legal_entity |
| `inn` | HashableEncryptedString(300) | YES | YES | Indexed (hash) | 10/12 digits, HMAC-SHA256 for search |
| `inn_hash` | String(64) | YES | — | YES | HMAC hash for indexed search |
| `kpp` | String(9) | YES | — | — | КПП (corrective account code) — plaintext |
| `ogrn` | String(15) | YES | — | — | ОГРН (legal entity registration) — plaintext |
| `ogrnip` | String(15) | YES | — | — | ОГРНИП (individual entrepreneur registration) — plaintext |
| `legal_name` | String(500) | YES | — | — | Company or individual name |
| `address` | Text | YES | — | — | Legal address |
| `tax_regime` | String(20) | YES | — | — | osno, usn, usn_d, usn_dr, patent, npd, ndfl |
| `bank_name` | String(200) | YES | — | — | Bank name |
| `bank_account` | EncryptedString(300) | YES | YES | — | Расчётный счёт — encrypted at rest |
| `bank_bik` | String(9) | YES | — | — | БИК (bank ID) — plaintext |
| `bank_corr_account` | EncryptedString(300) | YES | YES | — | Корреспондентский счёт — encrypted at rest |
| `yoomoney_wallet` | EncryptedString(300) | YES | YES | — | YooMoney wallet ID — encrypted at rest |
| `passport_series` | EncryptedString(300) | YES | YES | — | Паспорт серия — encrypted at rest |
| `passport_number` | EncryptedString(300) | YES | YES | — | Паспорт номер — encrypted at rest |
| `passport_issued_by` | EncryptedString(1000) | YES | YES | — | Issued by (agency) — encrypted at rest |
| `passport_issue_date` | Date | YES | — | — | Date only (no time) |
| `inn_scan_file_id` | EncryptedString(500) | YES | YES | — | Telegram file_id for INN scan |
| `passport_scan_file_id` | EncryptedString(500) | YES | YES | — | Telegram file_id for passport scan |
| `self_employed_cert_file_id` | EncryptedString(500) | YES | YES | — | Свидетельство НПД — encrypted at rest |
| `company_doc_file_id` | EncryptedString(500) | YES | YES | — | ОГРН/ОГРНИП doc scan — encrypted at rest |
| `is_verified` | Boolean | NO | — | — | Manual admin flag (no auto-verification logic exists) |
| `verified_at` | DateTime(tz) | YES | — | — | Timestamp when marked verified |
| `created_at` | DateTime(tz) | NO | — | — | TimestampMixin |
| `updated_at` | DateTime(tz) | NO | — | — | TimestampMixin |

**Migration reference:** `src/db/migrations/versions/0001_initial_schema.py`, lines 631–683.

---

### 2. Legal Status Enum Values

**ORM model field:** `legal_status` (String)  
**Pydantic schema:** `LegalStatus` enum  
**Location:** `src/api/schemas/legal_profile.py`, lines 12–16

```python
class LegalStatus(str, Enum):
    legal_entity = "legal_entity"
    individual_entrepreneur = "individual_entrepreneur"
    self_employed = "self_employed"
    individual = "individual"
```

**Note:** Plan refers to these as `legal_type` with values `(individual, self_employed, ie, llc)`. Actual enum names differ:
- Plan `ie` → actual `individual_entrepreneur`
- Plan `llc` → actual `legal_entity`
- Plan terminology `legal_type` → actual terminology `legal_status`

This is a **terminology gap** — the plan must be aligned to refer to `legal_status`, not `legal_type`.

---

### 3. Required Fields by Legal Status

**Source:** `src/core/services/legal_profile_service.py`, lines 21–79 (`_REQUIRED_FIELDS_MAP`)

| Legal Status | Fields | Scans | Bank Details | Passport | YooMoney | Tax Regime Required |
|---|---|---|---|---|---|---|
| **legal_entity** | legal_name, inn, kpp, ogrn, address, bank_name, bank_account, bank_bik, bank_corr_account | inn, company_doc | YES | NO | NO | NO |
| **individual_entrepreneur** | legal_name, inn, ogrnip, address, bank_name, bank_account, bank_bik, bank_corr_account | inn | YES | NO | NO | YES (must set) |
| **self_employed** | legal_name, inn, yoomoney_wallet | self_employed_cert | NO | NO | YES | NO (defaults to npd) |
| **individual** | legal_name, passport_series, passport_number, passport_issued_by, passport_issue_date | passport | NO | YES | NO | NO (defaults to ndfl) |

**Validation pattern:** Service method `check_completeness()` (line 169) iterates through required fields and sets `User.legal_status_completed = True/False` only if all are non-NULL and non-empty string.

**Note:** No field-level required validation at Pydantic layer (all fields optional in schema). Validation happens at service layer post-creation.

---

### 4. Missing Fields (Phase 3 §3.B.7 Gap)

The following fields are **NOT PRESENT** in current implementation but are required per Phase 3 plan:

| Field | Plan Type | Purpose | Status |
|-------|-----------|---------|--------|
| `fns_verification_status` | Enum["unchecked", "active", "inactive"] | Track НПД status for self_employed | **MISSING** |
| `fns_verified_at` | DateTime \| None | Timestamp of last ФНС check | **MISSING** |
| `egrul_snapshot_at` | DateTime \| None | Freshness timestamp for ЕГРУЛ/ЕГРИП | **MISSING** |
| `inn_checksum_valid` | Boolean | Result of INN checksum validation | **MISSING** |

**Verification:** Grep across model/schema/migration confirms zero occurrences.

---

### 5. Repository Methods

**File:** `src/db/repositories/legal_profile_repo.py`

| Method | Signature | Returns | Read/Write |
|--------|-----------|---------|-----------|
| `get_by_user_id(user_id)` | `async def get_by_user_id(self, user_id: int) -> LegalProfile \| None` | Single or None | READ |
| `create(user_id, **kwargs)` | `async def create(self, user_id: int, **kwargs) -> LegalProfile` | LegalProfile | WRITE |
| `update(user_id, **kwargs)` | `async def update(self, user_id: int, **kwargs) -> LegalProfile` | LegalProfile | WRITE |
| `update_scan(user_id, scan_field, file_id)` | `async def update_scan(self, user_id: int, scan_field: str, file_id: str) -> None` | None | WRITE |

**Base class:** `BaseRepository[LegalProfile]` (provides generic CRUD: `get_by_id()`, `list()`, etc.)

**No specialized methods for compliance queries** — no methods like `get_verification_status()` or `get_by_fns_status()` exist yet.

---

### 6. Frontend (Web Portal) Pattern Chain: screen → hook → api

**Screens:**
- `web_portal/src/screens/common/LegalProfileView.tsx` — read-only display + redirect to setup
- `web_portal/src/screens/common/LegalProfileSetup.tsx` — create/update form
- `web_portal/src/screens/common/LegalProfilePrompt.tsx` — initial nudge

**Hook:** `web_portal/src/hooks/useLegalProfileQueries.ts`, lines 1–65
- `useMyLegalProfile()` — GET query
- `useCreateLegalProfile()` — POST mutation
- `useUpdateLegalProfile()` — PATCH mutation
- `useValidateInn()` — POST validation
- `useRequiredFields(legalStatus)` — GET query
- `useValidateEntity()` — POST validation

**API module:** `web_portal/src/api/legal.ts`, lines 1–91
- `getMyLegalProfile()`
- `createLegalProfile(data)`
- `updateLegalProfile(data)`
- `skipLegalPrompt()`
- `validateInn(inn)`
- `getRequiredFields(legalStatus)`
- `validateEntity(data)` — calls `/api/legal-profile/validate-entity`

All endpoints prefixed with `/api/legal-profile/` (singular, not plural). **Correct pattern:** screen never imports api directly; hook wraps React Query; api module only place with fetch.

---

### 7. Mini App Compliance ✓

**File:** `mini_app/src/screens/common/LegalProfileView.tsx`

**Verdict:** COMPLIANT with ФЗ-152. Screen contains:
```tsx
// Phase 1 §1.B.2 placeholder.
// The previous mini_app implementation displayed inn / bank_account / tax_regime 
// — full PII surface. Per ФЗ-152 these fields live only in the web portal
```

**Behavior:** Displays message "Просмотр и редактирование реквизитов выполняется в веб-портале" + link to web portal. Zero PII fields rendered in mini_app.

**Note:** `AdvertiserFrameworkContract.tsx`, `AcceptRules.tsx`, `MainMenu.tsx` contain the word "legal" only in comment or contract-related contexts, not legal_profile data.

---

### 8. Encryption Status

**Per 16.x PII series (`CHANGES_2026-04-30_pii-encryption-at-rest.md`):**

| Field | Encrypted | Implementation |
|-------|-----------|-----------------|
| `inn` | YES | `HashableEncryptedString(300)` |
| `passport_series`, `passport_number`, `passport_issued_by` | YES | `EncryptedString(300)` / `EncryptedString(1000)` |
| `bank_account`, `bank_corr_account` | YES | `EncryptedString(300)` |
| `yoomoney_wallet` | YES | `EncryptedString(300)` |
| Scan file_ids | YES | `EncryptedString(500)` |
| `kpp`, `ogrn`, `ogrnip`, `bank_bik`, `tax_regime` | NO | Plaintext (String/Text) |

**Key canonicalization:** Per `CHANGES_2026-04-30_16-5b-pii-keys-canonical.md`, all `EncryptedString` fields use single master key from settings (no per-field key derivation). INN uses `HashableEncryptedString` for indexed search (HMAC-SHA256 hash stored separately).

---

### 9. Audit Log Integration — MISSING

**Current state:** Service methods `create_profile()`, `update_profile()`, `upload_scan()` make mutations but **DO NOT log** to `audit_log` table.

**Audit log structure exists:** `src/db/models/audit_log.py` shows entity_type can be "legal_profile", but no service code invokes audit logging for these mutations.

**Implication:** Compliance audit trail is incomplete. Any change to legal_profile fields (inn, bank details, verification status) bypasses audit logging.

**Code evidence:**
- `legal_profile_service.py`: Zero imports of audit logging
- `legal_profile_repo.py`: Pure data access, no audit hooks

---

### 10. Tests

**Integration tests:** `tests/integration/test_legal_profile_service.py`, `tests/integration/test_api_legal_profile.py` (read-only, not inspected for mutations tested)

**Unit test snapshot:** `tests/unit/snapshots/legal_profile_response.json` (contract drift guard per CLAUDE.md).

---

## Architectural Assessment

### What is Clean ✓

1. **Encryption consistency:** All sensitive PII encrypted via single master key. INN searchable via HMAC hash. Matches 16.x canonicalization.
2. **ORM ↔ Migration sync:** Fields match between `legal_profile.py` model and `0001_initial_schema.py` migration (verified via grep).
3. **Status completion logic:** `check_completeness()` correctly iterates required-fields map and sets user flag. Tax regime auto-defaults per status (npd for self_employed, ndfl for individual).
4. **Mini_app ФЗ-152 compliance:** Correctly excluded from mini_app; PII-sensitive endpoints web_portal-only.
5. **Frontend pattern chain:** screen→hook→api chain enforced. No direct API calls in screens.
6. **Document scan abstraction:** Unified `upload_scan()` method with typed scan_field enum.

### What is Inconsistent/Hack

1. **Audit logging absence:** Mutations skip audit trail entirely. For a compliance-critical model (legal_type affects gate checks, tax calculations, payout methods), this is a significant gap. Phase 3 gates will rely on legal_status field state; changes to that field should be auditable.

2. **No validation on update:** `update_profile()` accepts partial updates and calls `_validate_documents_for_status()` only if status is being changed. If caller updates `bank_account` without changing status, no document validation happens. This is correct (partial updates shouldn't re-validate), but it masks the broader issue: document mismatch could exist mid-update if user edits documents separately from status change.

3. **Completeness check fires on every update:** `check_completeness()` runs after every create/update, even for unrelated field changes (e.g., updating bank_name when no bank-related fields were required). Cheap enough, but unnecessary.

4. **Terminology mismatch (Plan vs Code):** Plan consistently uses `legal_type`; code uses `legal_status`. Causes reading friction and potential copy-paste bugs in implementation phase if not resolved. **Recommend:** Pin all Phase 3 references to `legal_status` in implementation plan.

### What is Missing Entirely

1. **Four compliance fields (3.B.7):** `fns_verification_status`, `fns_verified_at`, `egrul_snapshot_at`, `inn_checksum_valid` required for gate G16 (tax receipt for self_employed) and entity freshness checks (ЕГРУЛ/ЕГРИП snapshot age).

2. **FNS integration:** `fns_validation_service.py` exists and validates checksums, but no mechanism to:
   - Store last-verified timestamp (`fns_verified_at`)
   - Track НПД status from external ФНС API (`fns_verification_status`)
   - Store ЕГРУЛ/ЕГРИП snapshot freshness (`egrul_snapshot_at`)

3. **Audit logging hooks:** No calls to `AuditLog.create()` in service layer.

4. **Repository methods for compliance:** No `get_verification_status()`, `get_by_fns_status()`, `get_expired_snapshots()` — gate-checkers will need to query directly or these need adding.

---

## Recommendations

### 1. Add Four Missing Fields to LegalProfile (Phase 3 Block)

**Rationale:** Gates G16 (tax receipt for self_employed) and G17 (VAT obligation for llc) depend on knowing:
- `fns_verification_status`: Is the self_employed's НПД status actually active (vs assumed)?
- `fns_verified_at`: When was this last checked? (For snapshot freshness policy: re-verify every N days?)
- `egrul_snapshot_at`: For ie/llc, how stale is the entity registration data? (Gate checker can enforce "must be <30 days old")
- `inn_checksum_valid`: Simple boolean flag to avoid re-calculating checksum on every gate check.

**Approach:**
```python
# In legal_profile.py, add:
fns_verification_status: Mapped[str | None] = mapped_column(
    String(20), nullable=True  # "unchecked", "active", "inactive"
)
fns_verified_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
egrul_snapshot_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
inn_checksum_valid: Mapped[bool | None] = mapped_column(
    Boolean, nullable=True  # default=False initially to force re-check
)
```

**Migration:** Edit `0001_initial_schema.py` legal_profiles table creation. Add columns at end of table definition (pre-prod exception per CLAUDE.md — allowed because 0001 is editable).

**Schema update:** Add fields to `LegalProfileCreate`, `LegalProfileResponse` in `src/api/schemas/legal_profile.py` (all optional for now; gates will populate on check).

**Backward compatibility:** All new fields default NULL; existing profiles do not break. Populating values is async (gate-checkers call FNS on first check).

---

### 2. Audit Log Integration (Phase 3 Mandatory)

**Rationale:** Legal profile mutations are compliance-critical. Any change to `legal_status`, `inn`, `fns_verification_status`, payout fields, or verification flag must be logged for regulatory audit trail (ФЗ-152, ФЗ-115 KYC audit).

**Approach:** Add to `legal_profile_service.py`:
```python
async def _log_mutation(self, user_id: int, entity_id: int, action: str, changes: dict) -> None:
    from src.db.models.audit_log import AuditLog
    audit = AuditLog(
        user_id=user_id,
        entity_type="legal_profile",
        entity_id=entity_id,
        action=action,  # "create", "update", "upload_scan"
        changes_json=changes,
    )
    self.session.add(audit)
    await self.session.flush()
```

**Call sites:** Inside `create_profile()`, `update_profile()`, `upload_scan()` after successful ORM mutations.

**Capture:** Log only changed fields (per Pydantic `exclude_unset=True` pattern). Example:
```python
await self._log_mutation(user_id, profile.id, "update", 
    {"inn": "redacted", "fns_verification_status": "active"})
```

---

### 3. Repository Methods for Gate-Checkers (Phase 3 Block)

**Rationale:** Phase 3 § 3.D.1 specifies gate-checkers must not use inline queries; all DB access through repositories.

**Add to LegalProfileRepo:**
```python
async def get_verification_status(self, user_id: int) -> str | None:
    """Get fns_verification_status for self_employed gate checks."""
    profile = await self.get_by_user_id(user_id)
    return profile.fns_verification_status if profile else None

async def get_expired_snapshots(self, days: int) -> list[LegalProfile]:
    """Get profiles with egrul_snapshot_at older than N days (for bulk refresh tasks)."""
    from datetime import datetime, timedelta
    result = await self.session.execute(
        select(LegalProfile).where(
            LegalProfile.egrul_snapshot_at < datetime.now(tz) - timedelta(days=days)
        )
    )
    return result.scalars().all()
```

---

### 4. Terminology Alignment in Phase 3 Plan (Procedural)

**Current:** Plan uses `legal_type` consistently (lines 486, 553, 557, 558).  
**Actual:** Codebase uses `legal_status`.

**Recommendation:** Update `IMPLEMENTATION_PLAN_ACTIVE.md` Phase 3 §3.A (Agent A prompt) and §3.B.7 to substitute all `legal_type` → `legal_status`. This prevents copy-paste bugs during implementation (gate-checker code will reference `placement.legal_profile.legal_status`, not `legal_type`).

---

### 5. Completeness Check Optimization (Phase 4 or later)

**Current:** `check_completeness()` runs after every update, iterating required fields even for unrelated updates.

**Deferred:** Not blocking Phase 3. Can optimize in Phase 4 by:
- Only re-check if `legal_status` changed or any required field was touched
- Cache required-fields map

---

## Phase Phasing

### Must-do for Phase 3
1. Add four fields to model, migration, schema
2. Add audit logging to service mutations
3. Add repository methods for gate-checkers
4. Update plan terminology references (legal_status)

### Phase 4 or later (ДС / G07 related)
- FNS integration Celery task to populate `fns_verified_at`, `fns_verification_status` asynchronously
- ЕГРУЛ/ЕГРИП snapshot refresh task
- Completeness check optimization
- Web portal UI to show verification status, snapshot age

### Series 17.x (parallel or preceding)
- Credits naming cleanup (separate from legal_profile, but touches field validation in some edge cases)

---

## Scope Expansion Log

**No expansion:** Audit stayed within legal_profile surface. Touched mini_app/web_portal as read-only to verify ФЗ-152 compliance (per scope). No execution of tests, migrations, or schema validation commands (read-only constraints).

---

## Open Questions

1. **FNS API integration timing:** Plan does not specify when `fns_verification_status` gets populated. Should gate-checkers call FNS synchronously on first G03/G06 check, or is there a background task that pre-populates? (Deferred to Marina/Implementation session.)

2. **Snapshot freshness policy:** ЕГРУЛ/ЕГРИП snapshots — how old is "too old"? 30 days? 90 days? (Compliance decision, deferred.)

3. **INN checksum re-validation:** Currently `validate_inn()` is static and re-calculates on every call. Should `inn_checksum_valid` flag cached in DB be checked first, and re-check only on manual update? (Performance decision, deferred.)

---

## Final Verification Checklist

- [x] All 23 current fields enumerated with types, encryption status, nullability
- [x] Enum values for legal_status verified (4 values)
- [x] Required fields mapping validated from service source
- [x] Migration schema matches ORM model (spot-checked inn, passport fields)
- [x] Repository methods listed (4 methods)
- [x] Frontend pattern verified (screen→hook→api)
- [x] Mini_app ФЗ-152 compliance confirmed
- [x] Encryption fields verified against 16.x series
- [x] Four missing fields confirmed absent from model/schema/migration
- [x] Audit logging confirmed absent from service mutations
- [x] No inline DB queries found in legal_profile_service.py (uses repo abstraction)
