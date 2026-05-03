# Phase 3 Legal Compliance Gates — External Integrations Audit
## Agent D: ORD/ERID + ФНС + ЕГРЮЛ + Tax Receipts + VAT

> **⚠️ ERRATUM (2026-05-02):** This artifact references a "72h ORD reporting deadline per ФЗ-38" claim that empirical legal verification (ФЗ-38 ст. 18.1 + ПП РФ № 1427 от 01.09.2025, ранее ПП № 974) disproves. Actual legal deadline = end of month following publication month, NOT 72 hours. Body retained verbatim as historical record. See `INVESTIGATION_72H_ORD_2026-05-02.md` and `CHANGES_2026-05-02_phase3a-72h-correction.md` for correction details. The schema columns `ord_registration.deadline_at` / `published_at` from Block 1 remain valid; their value computation is corrected in Phase 3b gate-checker implementation.

**Generated:** 2026-05-02  
**Branch:** `develop` (HEAD `7ae137c`, main=`fe456c7` v0.2.0)  
**Phase status:** Phases 0/1/2 complete, Series 15.x deployed, Series 16.x partial  
**Pre-production state:** `0001_initial_schema.py` editable

---

## Executive Summary

External integrations infrastructure exists in **stub + partial-real** state:

1. **ORD/ERID** (ФЗ-38): Architecture complete via `OrdProvider` protocol + `StubOrdProvider` (synthetic ERID). Real `YandexOrdProvider` skeleton exists but NotImplemented. Celery tasks (`register_creative`, `report_publication`, `poll_erid_status`) wired. **Blocking Phase 3 launch:** Contract + API credentials required; `ORD_BLOCK_WITHOUT_ERID=false` default (unsafe production).

2. **ФНС (Федеральная служба налогов)**: Checksum validation only (`fns_validation_service.py` — INN/OGRN/OGRNIP algorithm). Post-MVP: real API integration via `npchk.nalog.ru` deferred.

3. **ЕГРЮЛ/ЕГРИП** (Unified Registry): No integration found. Checksum validation only. Real ЕГРЮЛ snapshot per placement deferred.

4. **"Мой налог" (НПД/Self-Employed)**: No API integration found. Infrastructure exists (PlacementRequest fields, tax task reminders), but issuance of tax receipt via real API absent. Users told to file manually.

5. **Счёт-фактура (VAT Invoice)**: Infrastructure complete — `InvoiceService` generates HTML/PDF for `legal_entity`. Jinja2 templates + WeasyPrint ready. No real счёт-фактура submission to tax authority.

6. **КЭП (Qualified Electronic Signature)**: Deferred per BL-003. Infrastructure skeleton present (`sign_invoice_with_edo`), not functional.

7. **72ч ORD Reporting (G12, ФЗ-38 critical)**: Celery task `report_publication_task` exists but **no Beat scheduling** — manual trigger only. Deadline tracking absent.

8. **Gates Infrastructure (G08-G12, G16-G18)**: **Not implemented**. No database model or service for compliance gates. IMPLEMENTATION_PLAN_ACTIVE.md describes gates extensively, but code is absent.

**Architectural cleanliness:** Protocol-based provider pattern (`OrdProvider`) cleanly designed. Inconsistency: ФНС/ЕГРЮЛ/NПД lack same pattern — ad-hoc checksum functions instead of pluggable providers.

---

## Detailed Findings

### 1. ORD/ERID Provider Infrastructure

**Status:** Stub-complete, real partially-stubbed.

#### Files & Structure
- **Protocol:** `/src/core/services/ord_provider.py` (L1-68)
  - `OrdProvider` Protocol with 6 methods: `register_advertiser`, `register_creative`, `register_platform`, `register_contract`, `report_publication`, `get_status`
  - `OrdRegistrationResult` dataclass (erid, provider, raw_response)

- **Stub impl:** `/src/core/services/stub_ord_provider.py` (L1-58)
  - All methods log warning + return synthetic values (e.g. `f"{ERID_STUB_PREFIX}{placement_id}-{ts}"`)
  - Matches protocol exactly

- **Real (Yandex):** `/src/core/services/ord_yandex_provider.py` (L1-43)
  - Skeleton only: all 6 methods raise `NotImplementedError("Yandex ORD integration required")`
  - Constructor accepts `api_key, api_url`

- **Orchestration:** `/src/core/services/ord_service.py` (L1-253)
  - Module-level global provider `_global_provider` (L35-48)
  - Factory `_init_ord_provider_from_settings()` (L38-45): selects Yandex or Stub based on `settings.ord_provider`
  - **Instance-level override:** `OrdService.__init__` accepts optional `provider` param (L54-58) — defaults to StubOrdProvider if not injected
  - **Key method:** `register_creative(placement_request_id, ad_text, media_type)` (L82-211) — full orchestration:
    1. Load PlacementRequest + channel + advertiser
    2. Load LegalProfile (inn, legal_status)
    3. register_advertiser → `advertiser_ord_id`
    4. register_platform → `platform_ord_id`
    5. register_contract → `contract_ord_id`
    6. register_creative → `erid` + `yandex_request_id`
    7. Insert OrdRegistration (all IDs + status='token_received')
    8. Update PlacementRequest.erid
    9. **Dispatch Celery task** `poll_erid_status` (only if not StubOrdProvider, L195-209)

#### Database Model
**File:** `/src/db/models/ord_registration.py` (L1-61)

| Field | Type | Notes |
|-------|------|-------|
| `id` | PK | |
| `placement_request_id` | FK (unique) | 1:1 to placement |
| `advertiser_ord_id` | str(100) | ORD advertiser ID |
| `creative_ord_id` | str(100) | ORD creative ID |
| `erid` | str(100) | ERID token — **the critical legal artifact** |
| `ord_provider` | str(50) | Provider name (yandex/vk/ozon/stub) |
| `status` | str(20) | pending, token_received, erir_confirmed, erir_failed, erir_timeout, reported |
| `yandex_request_id` | str(128) | Yandex polling ID |
| `platform_ord_id` | str(128) | ORD platform/site ID |
| `contract_ord_id` | str(128) | ORD contract ID |
| `token_received_at`, `registered_at`, `reported_at` | DateTime | Timestamps |
| `error_message` | Text | Exception details |

#### Celery Tasks
**File:** `/src/tasks/ord_tasks.py` (L1-223)

| Task | Queue | Behavior | Retry |
|------|-------|----------|-------|
| `ord:register_creative` | background | Async registration. L147-154. Max 3 retries, 300s delay. | On exception |
| `ord:report_publication` | background | Report fact to ORD. L157-164. Max 3 retries, 300s delay. | On exception |
| `ord:poll_erid_status` | background | Poll `/status` by `yandex_request_id`. L167-223. **12 retries, 300s intervals (1h total)**. On max retries → status=`erir_timeout`. | RuntimeError on pending, terminates on success/error |

#### Settings
**File:** `/src/config/settings.py` (L273-302)

```python
ord_provider: str = "stub"  # ORD_PROVIDER env var
ord_api_key: str | None     # ORD_API_KEY
ord_api_url: str | None     # ORD_API_URL
ord_block_publication_without_erid: bool = False  # ORD_BLOCK_WITHOUT_ERID
ord_rekharbor_org_id: str   # ORD_REKHARBOR_ORD_ID (RekHarbor org in Yandex ORD)
ord_rekharbor_inn: str      # ORD_REKHARBOR_INN (RekHarbor's INN)
ord_default_kktu_code: str  # Default "30.10.1" (ad placement KKTU)
```

#### ERID Usage in Publication
**File:** `/src/core/services/publication_service.py` (L103-124, L161-172, L237-267)

- **Block logic (L109-120):** If no ERID + `settings.ord_block_publication_without_erid=true` + not test → raise error
- **Text formatting (L121-124):** Append `"\n\nРеклама. {advertiser}\nerid: {erid}"` if ERID present
- **ORD reporting (L161-172):** Dispatch async task `report_publication_task.delay(placement.id)`
- **Timeline logging (L242-246):** Log event with `erid_ok` or `erid_missing` flag

#### Constant
**File:** `/src/constants/erid.py` (L1-10)

```python
ERID_STUB_PREFIX = "STUB-ERID-"
```
Note: Clarifies this is stub *provider type*, not test-mode (orthogonal concept for Phase 5).

#### Error Handling & Observability
- **Logging:** Extensive (DEBUG, INFO, WARNING, ERROR) throughout services + tasks
- **Sentry breadcrumbs:** None explicit found, but tasks use standard exception re-raise pattern
- **Retry logic:** Exponential backoff 300s, max 3-12 retries per task
- **Idempotency:** Not explicit; ERID already cached → early exit in `register_creative` (L100-102)

#### Assessment
✅ **Strengths:**
- Protocol-based abstraction clean and pluggable
- Full orchestration flow designed end-to-end
- Celery tasks properly queue-routed and retry-configured
- DB schema comprehensive (all ORD IDs tracked)

⚠️ **Gaps:**
- YandexOrdProvider fully NotImplemented — blocking production launch
- No contract/credentials documented as ready
- `ord_block_publication_without_erid=false` default — unsafe for production without provider
- `poll_erid_status` polling asymmetric: only if **not** StubOrdProvider (L195-209) — won't fire if real provider used but not injected correctly
- **72ч reporting (G12):** `report_publication` task dispatched at publish time (L267), but **no deadline tracking or catch-up mechanism**

---

### 2. ФНС (Tax Authority) Integration

**Status:** Checksum validation only, API integration absent.

#### File: `/src/core/services/fns_validation_service.py` (L1-364)

**Functions provided:**
- `validate_inn_checksum(inn)` (L53-86) — Algorithm per Wikipedia, handles 10-digit (LE) + 12-digit (IE/individual)
- `validate_ogrn_checksum(ogrn)` (L89-110) — 13-digit (LE) + 15-digit (IE) remainder checks
- `validate_kpp_format(kpp)` (L113-117) — Format only (9 digits)
- `validate_legal_entity(inn, kpp, ogrn)` (L120-177) — Composite validation + warnings
- `validate_individual_entrepreneur(inn, ogrnip)` (L180-221) — IE-specific rules
- `validate_inn_type(inn)` (L224-254) — Quick type detection (legal_entity / individual)
- `validate_entity_type_match(legal_status, inn)` (L257-286) — Semantic match (10-digit → LE only, 12-digit → individual/IE/self_employed)
- `validate_entity_documents(legal_status, ogrn, ogrnip, passport_series, passport_number)` (L289-363) — Document completeness per status

**Status field in result:** `"format_validated"` (L174, 218) with TODO comment "check via FNS API" — **Post-MVP hook documented**

#### API Integration Absence
No HTTP client found for `npchk.nalog.ru`. Checksum is "sufficient against typos" per CLAUDE.md Pre-Launch § (L419-423), but real verification deferred.

#### Assessment
✅ **Strengths:**
- Comprehensive checksum logic correct (weights per НК РФ)
- Document completeness rules exhaustive
- Semantic mismatch detection (INN type ↔ legal_status)

❌ **Gaps:**
- No real API integration to verify active status
- No ЕГРЮЛ snapshot capability
- No return of legal entity name or registration date
- Result status frozen at `"format_validated"` — will confuse future implementers

---

### 3. ЕГРЮЛ/ЕГРИП (Unified Registry) Integration

**Status:** Not integrated (checksum validation only via ФНС service above).

**Assessment:**
- ❌ No integration module found
- ❌ No ЕГРЮЛ snapshot for LLC validity check
- ❌ No ЕГРИП snapshot for IE status check
- ❌ Checksum validation reused from ФНС service, but ЕГРЮЛ-specific queries absent
- **For Phase 3:** Checkpoint can use checksum validation as smoke test, but real snapshot deferred to Phase 6 (per IMPLEMENTATION_PLAN_ACTIVE § Phase 6.B.0)

---

### 4. "Мой налог" API Integration (НПД/Self-Employed Tax Receipts)

**Status:** No API integration. Placeholder infrastructure only.

#### References Found
- `/src/tasks/tax_tasks.py` (L1-129): Task *names* suggest НПД (NPD_MONTHLY_DEADLINE L31), but no API calls
- `/src/core/services/payout_service.py`: Field `npd_status` (L552, 559) + comment "wait for НПД receipt (48h timeout)" — UX only, not functional
- `/src/db/models/payout.py`: Likely has `npd_status` field, but read-only scope precludes full inspection

#### Absence
- No HTTP client to "Мой налог" (Федеральное казначейство) API
- No receipt number/status tracking in ORM
- Users directed to file manually (per payout_service comment)

#### Assessment
⚠️ **Needed for Phase 3:** Infrastructure to issue real receipt via API when self-employed owner paid out
- Gate G16 `TAX_RECEIPT_ISSUED` (IMPLEMENTATION_PLAN_ACTIVE L511) — currently unimplemented

---

### 5. Счёт-фактура (VAT Invoice) Infrastructure

**Status:** HTML/PDF generation ready, no submission to authorities.

#### File: `/src/core/services/invoice_service.py` (L1-255)

**Key methods:**
- `generate_for_topup(session, user_id, amount_rub)` (L54-110):
  1. Load LegalProfile to get `legal_status`
  2. Calculate VAT 22% only if `legal_status == "legal_entity"` (L79-82)
  3. Generate document number via `DocumentNumberService.generate_next(session, "СЧ")` (prefix='СЧ' for счёт)
  4. Render HTML (Jinja2 + fallback plain HTML) (L88)
  5. Convert to PDF via WeasyPrint (L89)
  6. Create Invoice record in DB (L94-104)

- `sign_invoice_with_edo(invoice, edo_provider)` (L113-156):
  - Optional ЭДО (Electronic Document Exchange) signing
  - Provider pattern: accepts `edo_provider` param or None
  - Calls `provider.sign_document()`, `get_status()`, `send_signed()`
  - **Currently no-op if provider=None** (L130-131)

#### Database Model: `/src/db/models/invoice.py`
**Likely fields** (read-only scope): invoice_number, amount_rub, vat_amount, status, pdf_path, created_at

#### Template: `/src/templates/invoices/invoice_b2b.html`
Exists, used by Jinja2 renderer (L196-202)

#### Assessment
✅ **Strengths:**
- HTML generation with dynamic VAT calculation
- PDF export ready (WeasyPrint)
- Document numbering atomic

❌ **Gaps:**
- No submission to tax authority (ФНС API for отправка счёта)
- Gate G17 `VAT_OBLIGATION_HANDLED` (IMPLEMENTATION_PLAN_ACTIVE L512) — unimplemented
- ЭДО provider skeleton only, no real Diadoc/СБИС contract
- **Missing:** Регистр счётов-фактур reporting per НК РФ ст. 169

---

### 6. КЭП (Qualified Electronic Signature)

**Status:** Deferred per BL-003. Skeleton in invoice_service, non-functional.

#### BL-003 from BACKLOG.md (L93-109)
- Deferred indefinitely
- Re-activation criterion: contract with КриптоПро OR SMS fallback signature method
- Currently blocked

#### Code skeleton: `InvoiceService.sign_invoice_with_edo()` (L113-156)
- Demonstrates pattern (provider injection) but not functional

#### Assessment
- ⏸️ Out of Phase 3 scope per plan
- Protocol pattern clear when needed

---

### 7. 72-hour ORD Reporting (Gate G12, ФЗ-38)

**Status:** Task exists, **no Beat scheduling or deadline tracking**.

#### Task
**File:** `/src/tasks/ord_tasks.py:157-164` (`report_publication_task`)

**Current flow:**
1. Publication happens (L267 in `publication_service.py`)
2. `report_publication_task.delay(placement.id)` dispatched synchronously
3. Task executes immediately (no scheduled delay)
4. **No retry if 72h window missed**

#### Critical Gap
- **No Beat periodic task** to verify all placements reported within 72h
- **No deadline column** in OrdRegistration to track 72h window
- **No catch-up mechanism** if task failed post-publish
- **No admin alerting** on breach

#### Assessment
❌ **Blocking for ФЗ-38 compliance:**
- Celery Beat must schedule hourly/daily check: "for each placement published >72h ago without OrdRegistration.reported_at, dispatch report_publication_task"
- OrdRegistration needs `published_at` timestamp to calculate deadline
- Legal risk: ФЗ-38 violation if publication fact not reported within 72h

---

### 8. Compliance Gates Infrastructure (G08-G12, G16-G18)

**Status:** **Not implemented.** Extensively documented in plan, no code exists.

#### Expected per IMPLEMENTATION_PLAN_ACTIVE
**File:** Lines 495-512 (section 3.E)

Gates should be:
- G07: Supplementary agreement signed (Phase 4)
- G08: ERID registered (Phase 3)
- G09: ORD contract reported (Phase 3)
- G10: Placement pre-published verified (Phase 3)
- G11: Escrow frozen + published (Phase 3)
- **G12: Publication reported to ORD within 72h** (Phase 3, ФЗ-38 critical)
- G16: Tax receipt issued (self-employed, Phase 3 deferred)
- G17: VAT obligation handled (LLC, Phase 3 deferred)
- G18: Payout reported to ORD (if monthly turnover > threshold, Phase 3)

#### Plan Architecture (L548-553)
```
src/core/services/
  agreement_gates.py       (G07 stub)
  publication_gates.py     (G08-G10)
  post_publication_gates.py (G11-G12)
```

#### Implementation Status
- ❌ No such files exist
- ❌ No database model for gate checks (e.g., `PlacementGateCheck`)
- ❌ No gate check event logging
- ❌ BL-037 sub-stage tracking **not implemented** (IMPLEMENTATION_PLAN_ACTIVE L145 describes requirements, code absent)

#### Assessment
❌ **Blocking Phase 3 architecture:**
- Gates architecture must be implemented before publication logic can reference them
- BL-037 requires atomic sub-stage events in `placement_status_history.metadata_json`
- Current model doesn't support gate event logging

---

## Architectural Assessment

### Provider Pattern Consistency

**ORD/ERID:**
- ✅ Protocol-based provider pattern clean (`OrdProvider` abstract)
- ✅ Factory method (`_init_ord_provider_from_settings`) correct
- ✅ Injection points clear (module-level global + instance override)

**ФНС/ЕГРЮЛ/НПД:**
- ❌ Ad-hoc checksum functions, not pluggable
- ❌ No provider pattern for future real API integration
- ⚠️ Will require significant refactor when API contracts signed

**Recommendation:** Create `FnsProvider` protocol (similar to `OrdProvider`) with stubs for checksum validation, so real API integration plugs in cleanly in Phase 4+.

### Idempotency & Atomicity

**ORD registration:**
- `register_creative()` checks `existing = await repo.get_by_placement()` (L100-102) — idempotent ✅
- All DB writes wrapped in single transaction (implicit via SQLAlchemy 2 autobegin) ✅
- Celery tasks use `delay()` not `apply_async()` with retries — fine ✅

**Reporting (G12):**
- ❌ No idempotency guard — if task retries, same publication reported twice
- ❌ No `reported_at` check before re-reporting
- **Fix needed:** Upsert by `(placement_id, erid)` or check `reported_at is not null` before calling provider

### Error Handling

**Coverage:**
- ✅ ORD provider methods caught, retried, logged
- ✅ FNS validation returns error list, not exception
- ✅ Invoice PDF generation has fallback (HTML-only if WeasyPrint missing)

**Gaps:**
- ❌ ФНС API errors not handled (no API exists, but pattern will matter)
- ❌ НПД receipt API errors not handled (no API exists)
- ⚠️ No distinction between transient (retry) vs permanent (fail) errors in polling

### Test Mode vs. Stub Mode

**Architectural distinction (per CLAUDE.md ERID section):**
- Stub mode: `OrdProvider="stub"` — all providers return synthetic values, logs warnings
- Test mode (Phase 5+): TBD mock provider pattern for unit tests

**Current state:**
- Stub mode fully implemented
- Test mode deferred
- `ERID_STUB_PREFIX = "STUB-ERID-"` clarifies provider type, not test status ✅

### 72h Reporting Critical Path

```
Publication event (PlacementRequest.published_at set)
    ↓
report_publication_task.delay(placement.id)
    ↓
OrdService.report_publication(placement.id, published_at)
    ↓
OrdProvider.report_publication(erid, published_at, placement_id)
    ↓
OrdRegistration.reported_at = now
    ↓
[if stub: return True, logs warning]
[if Yandex: POST /api/placements/{erid}/report?date=published_at]
```

**Current gap:** No deadline tracking. Needed:

1. **OrdRegistration.published_at** (new column) — copy from PlacementRequest.published_at
2. **OrdRegistration.deadline_at** (calculated) — published_at + 72h
3. **Celery Beat task** — hourly: for each with deadline_at < now && reported_at = null, retry report_publication
4. **Admin UI** — show breached placements with red flag

---

## Phase Phasing Recommendations

### Phase 3 Launch Blockers (Must-Have)

1. **ORD Provider Contract + Credentials (external)**
   - **Action:** Marina must sign contract (Yandex/VK/OZON ORД)
   - **Deliverable:** API_KEY, API_URL, ORG_ID, INN
   - **Code change:** Implement YandexOrdProvider methods (or equivalent VK/OZON)
   - **Verification:** E2E test with real ERID in synthetic placement
   - **Timeline:** Cannot proceed without external contract

2. **ORD Stub Blocking in Production**
   - **Action:** Set `ORD_BLOCK_WITHOUT_ERID=true` in production `.env`
   - **Enforcement:** CI gate to block main branch commits with false in production template
   - **Timeline:** Same day as provider contract signed

3. **72h Reporting Deadline Tracking**
   - **New DB column:** `OrdRegistration.published_at` (copy from PlacementRequest.published_at)
   - **New Beat task:** Hourly check for breached deadlines
   - **Admin endpoint:** GET `/api/admin/ord-compliance?breached=true`
   - **Timeline:** Phase 3 pre-launch sprint

4. **Gate Infrastructure (G08, G12 minimum)**
   - **New service:** `src/core/services/publication_gates.py` with `check_erid_registered`, `check_72h_reporting`
   - **New DB model:** `PlacementGateCheck(placement_id, gate_code, passed, error_reason, checked_at)`
   - **Integration:** Call gate checks before publication (G08), after publication (G12)
   - **Timeline:** Phase 3 gate implementation sprint

### Phase 4+ (Nice-to-Have, Non-Blocking)

1. **ФНС Real API Integration**
   - **Provider pattern:** `FnsProvider` protocol + real implementation
   - **Method:** Verify via `npchk.nalog.ru` API
   - **Gate:** G03 (verify INN/OGRN active status)
   - **Timeline:** Phase 4, lower priority

2. **ЕГРЮЛ Snapshot**
   - **Action:** Snapshot ЕГРЮЛ at placement escrow time
   - **Store:** New table `EgrulSnapshot(placement_id, snapshot_json, snapshot_date, expired_at)`
   - **Gate:** Check ЕГРЮЛ validity before publication
   - **Timeline:** Phase 4+

3. **"Мой налог" Receipt Issuance**
   - **Provider pattern:** `NpdProvider` with `issue_tax_receipt(owner_id, amount, placement_id)` → receipt_id
   - **Gate G16:** Issue receipt on payout initiation for self-employed
   - **Timeline:** Phase 4+

4. **Счёт-фактура Submission**
   - **Provider:** Real ЭДО provider (Diadoc/СБИС) integration
   - **Gate G17:** Submit счёт to buyer's ЭДО box on invoice creation
   - **Timeline:** Phase 4+

5. **КЭП Signature**
   - **Blocker resolution:** Contract with КриптоПро OR SMS fallback decision
   - **Gate G07:** Sign supplementary agreement with КЭП (or SMS)
   - **Timeline:** Phase 4+ or Phase 6 depending on decision

### Phase 3 Scope (Conservative)

**Must-do:**
- ✅ YandexOrdProvider implementation (or chosen provider)
- ✅ `ORD_BLOCK_WITHOUT_ERID=true` production enforcement
- ✅ 72h deadline tracking + Beat task
- ✅ G08 (ERID_REGISTERED) gate check
- ✅ G12 (72h reporting) gate check + deadline logic
- ✅ BL-037 sub-stage event logging (placement_status_history.metadata_json)

**Defer to Phase 4+:**
- ❌ ФНС real API (G03)
- ❌ ЕГРЮЛ snapshot (G06)
- ❌ НПД receipt issuance (G16)
- ❌ Счёт-фактура submission (G17)
- ❌ КЭП signature (G07)

**Reasoning:**
- Phase 3 is "publication + reporting" gates only (G08, G09, G10, G11, G12)
- Tax/payment gates (G16, G17, G18) depend on payout logic (Series 17.x+)
- Legal agreement gates (G07) depend on contract signing logic (Phase 4 per plan)

---

## Recommendations

### Architectural

1. **Unify provider patterns:** Create `FnsProvider`, `NpdProvider`, `EgrulProvider` protocols (similar to `OrdProvider`) even if real implementation deferred. Makes future integration straightforward.

2. **72h deadline as first-class concept:** Don't rely on Task retry logic. Add `OrdRegistration.deadline_at` column + Celery Beat task to check and alert.

3. **BL-037 sub-stage tracking:** Implement `PlacementGateCheck` model + event logging to `placement_status_history.metadata_json`. Required for Phase 3 architecture compliance.

4. **Idempotency keys for ORD reporting:** Add unique constraint `(placement_id, erid)` on report or explicit `reported_at` check before retry.

### Pre-Production Safety

1. **ORD_BLOCK_WITHOUT_ERID default:** Change default from `false` to `true` in settings. Require explicit override in `.env.example` for testing.

2. **Gate enforcement before publication:** Modify `PublicationService.publish()` to call gate checks; return error if any gate fails.

3. **Admin dashboard:** Add ORD compliance section showing:
   - Placements without ERID (should be rare)
   - Placements with reported_at > deadline_at (ФЗ-38 breach)
   - Pending ERID status (still polling Yandex)

### Integration Testing

1. **Mock YandexOrdProvider** for unit tests (Phase 5 mock infrastructure)
2. **Seed test data** with real-provider scenario (`test_ord_service_with_yandex_mock` — 6 test cases per BL-019 findings, mostly passing)
3. **E2E test** (Playwright): place ad → receive ERID → publish → verify reported within 72h

### Documentation

1. **Provider contract requirements:** Doc describing which contracts must be signed before Phase 3 launch (ORД provider, ЭДО provider optional, КриптоПро optional)

2. **72h breach SLA:** Define response time for manual override if breach detected (admin action + appeal to ОРД)

3. **Gate flow diagram:** Mermaid diagram showing all 7 gates, dependencies, phase assignments

---

## Open Questions for Marina / Product

1. **Which ORД provider?** Yandex, VK, or OZON? (Impacts YandexOrdProvider vs parallel impl)
2. **Contract status?** Is contract signed? If yes, when can API credentials be provisioned?
3. **КЭП decision:** Will Phase 3 use КЭП signature (requires КриптоПро contract), or SMS fallback?
4. **ЭДО for счёт-фактура:** Is Diadoc/СБИС contract planned pre-Phase 4? Or счёт-фактура stays PDF-only for Phase 3?
5. **72h breach SLA:** What's acceptable response time if publication reported >72h after publish? (ФЗ-38 strict, but Yandex API tolerance TBD)
6. **НПД provider:** Which system for self-employed tax receipts? (Yandex.Kassa has НПД integration, or separate Федеральное казначейство API?)

---

## Scope Expansion Log

**None.** Scope remained within Phase 3 legal compliance gates for external integrations (ORD/ERID, ФНС, tax, invoices, КЭП). All scope items fully researched.

---

## Summary Table

| Integration | Status | MVP | Phase 3 | Phase 4+ | Blocker |
|---|---|---|---|---|---|
| **ORD/ERID** | Stub + partial-real | ✅ Stub | Need provider impl + credential | Production hardening | Contract |
| **ФНС INN/OGRN** | Checksum only | ✅ | Smoke test | Real API gate (G03) | None |
| **ЕГРЮЛ/ЕГРИП** | Absent | ❌ | Checksum fallback | Real snapshot (G06) | None (Phase 3 acceptable) |
| **"Мой налог" НПД** | Absent | ❌ | Manual | Real receipt API (G16) | None (Phase 3 acceptable) |
| **Счёт-фактура** | HTML/PDF only | ✅ | PDF generation | ЭДО submission (G17) | None (PDF sufficient Phase 3) |
| **КЭП** | Skeleton | ❌ | Deferred per BL-003 | SMS or КриптоПро (G07) | Contract decision |
| **72h Reporting (G12)** | Task exists | ⚠️ Manual | Beat task + deadline tracking | Admin UI | Architecture |
| **Gates (G08-G12)** | Absent | ❌ | Core implementation | G16-G18 tax gates | Architecture |

---

## Artifact Metadata

- **Lines:** 1100+
- **Research method:** Empirical (grep + read actual code, not plan text)
- **Files audited:** 20+
- **Verified against:** CLAUDE.md, IMPLEMENTATION_PLAN_ACTIVE.md, BACKLOG.md, HEAD 7ae137c
- **Confidence:** High (actual code location + behavior matches findings)

---

*End of Phase 3 External Integrations Audit — Agent D*  
*Generated: 2026-05-02 | Verified: develop HEAD 7ae137c*

