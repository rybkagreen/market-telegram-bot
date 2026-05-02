# Phase 3 Legal Compliance Gates — Research Consolidation

> **⚠️ ERRATUM (2026-05-02):** This artifact references a "72h ORD reporting deadline per ФЗ-38" claim that empirical legal verification (ФЗ-38 ст. 18.1 + ПП РФ № 1427 от 01.09.2025, ранее ПП № 974) disproves. Actual legal deadline = end of month following publication month, NOT 72 hours. Body retained verbatim as historical record. See `INVESTIGATION_72H_ORD_2026-05-02.md` and `CHANGES_2026-05-02_phase3a-72h-correction.md` for correction details. The schema columns `ord_registration.deadline_at` / `published_at` from Block 1 remain valid; their value computation is corrected in Phase 3b gate-checker implementation.

**Date:** 2026-05-02
**Branch state:** `main = fe456c7` (tag v0.2.0), `develop = 7ae137c`
**Source artifacts:**
- `reports/docs-architect/discovery/PHASE3_RESEARCH_AGENT_A_2026-05-02.md` — `legal_profile` structure (412 lines)
- `reports/docs-architect/discovery/PHASE3_RESEARCH_AGENT_B_2026-05-02.md` — scattered legal/gate-like checks (791 lines)
- `reports/docs-architect/discovery/PHASE3_RESEARCH_AGENT_C_2026-05-02.md` — payout/billing + bot residue (619 lines)
- `reports/docs-architect/discovery/PHASE3_RESEARCH_AGENT_D_2026-05-02.md` — external integrations (582 lines)

**Consolidation method:** Full read of all 4 artifacts + cross-validation pass (overlaps, contradictions, gaps) + reasoning per principles. Findings here SUPERSEDE individual agent recommendations where reasoning is stronger; artifacts retained for deep detail (line-level refs preserved via citation).

---

## Executive summary

Phase 3 Legal Compliance Gates as scoped in `IMPLEMENTATION_PLAN_ACTIVE.md` § 3 (lines 460-615) is a **substantially larger effort than the 8-10ч budget suggests** — combined empirical findings indicate ~30-40ч realistic effort if executed at full scope, primarily because the centralized gate framework (`LegalComplianceService` + 18-gate enum + 6 gate-checker modules + BL-037 sub-stage tracking + 72ч ORD Beat infrastructure) does not exist anywhere in code today and must be built from scratch.

What exists today is **scattered partial state**: legal-precondition checks live inline across 14 files with inconsistent error classes, S-48 transaction-contract violations in 3 specific sites (`channels.py:411-423`, `contracts.py:67`, `contracts.py:134`), no centralized gate evaluation, no metadata wiring, and no audit-log integration on either legal_profile mutations or payout admin actions. ORD/ERID has the cleanest provider abstraction (Protocol pattern + StubOrdProvider production-functional) but the real `YandexOrdProvider` is a `NotImplementedError` skeleton. ФНС is checksum-only. ЕГРЮЛ, Мой налог, ЭДО for счёт-фактура, КЭП — none integrated.

What is **clean and ready to build on**: 16.x PII series complete (encryption at rest, admin pinning, bot payout flow architecturally removed and verified empirically); 17.3 credits/balance rename clean in payout code; payout services S-48 compliant; `placement_status_history.metadata_json` ready as a JSONB target for gate-event recording; ORD Protocol pattern reusable as template for `FnsProvider`/`NpdProvider`/`EgrulProvider` even if implementations stay deferred.

The two largest decisions Marina must make before Implementation begins are **(D1) the Phase 3 scope width** — whether G13-G18 (completion/tax/payout gates) land in Phase 3 with stubs, defer entirely to Phase 4, or split granularly per gate based on existing infrastructure — and **(D3) the ORD provider contract status**, because production-blocking ORD launch is gated externally and `ORD_BLOCK_WITHOUT_ERID=true` cannot flip until credentials arrive. A plan terminology drift (plan uses `legal_type`, code uses `legal_status` with different enum values) needs an alignment commit before Phase 3 implementation begins to prevent copy-paste bugs.

**Recommended sequencing:** Phase 3a foundation (terminology alignment + migration + service skeleton + S-48 fixes), Phase 3b gate implementation (granular per gate per D1), Phase 3c integration (transition wiring + channel-add precondition + audit log), Phase 3d API + acceptance. Implementation should be split across 3-4 sub-sprints, not landed as a single atomic Phase 3 commit, due to scope.

---

## 1. Current state baseline

### 1.1 `legal_profile` structure (Agent A)

The `LegalProfile` ORM model contains 23 fields across model + `0001_initial_schema.py` migration (verified in sync; lines 631-683 of migration). The enum is named **`legal_status`** with four values: `individual`, `individual_entrepreneur`, `self_employed`, `legal_entity` — note this differs from the plan's vocabulary (see § 2.2 contradiction).

PII fields (INN, passport series/number/issued_by, bank account/corr_account, YooMoney wallet, all scan file_ids) are encrypted at rest via `EncryptedString` / `HashableEncryptedString` with a single master key per 16.5b canonicalization. INN is HMAC-SHA256-indexed via the separate `inn_hash` column for searchability. Plaintext fields are limited to non-PII identifiers (`kpp`, `ogrn`, `ogrnip`, `bank_bik`, `tax_regime`).

Per-`legal_status` required-fields validation lives at the service layer (`LegalProfileService._REQUIRED_FIELDS_MAP`, lines 21-79 of `legal_profile_service.py`), iterating in `check_completeness()` (line 169) which sets `User.legal_status_completed`. Pydantic schemas keep all fields optional — validation is post-create, not per-field. Repository exposes 4 methods (`get_by_user_id`, `create`, `update`, `update_scan`); no specialized compliance-query methods exist (`get_verification_status`, `get_expired_snapshots`, etc.).

Mini_app compliance is correct (`LegalProfileView.tsx` is a deliberate redirect placeholder — `// Phase 1 §1.B.2 placeholder.` — with zero PII surface, per ФЗ-152). The web_portal honours the `screen → hook → api-module` chain (`useLegalProfileQueries.ts` + `api/legal.ts`).

**Two concrete absences blocking Phase 3:**
1. Four compliance fields are entirely missing from model/schema/migration: `fns_verification_status`, `fns_verified_at`, `egrul_snapshot_at`, `inn_checksum_valid`.
2. **No mutation goes to `audit_log`.** `create_profile`, `update_profile`, `upload_scan` all write to ORM and return — no `AuditLog.create()` call anywhere in the service. `audit_log` model itself accepts `entity_type="legal_profile"`, but no code emits.

### 1.2 Scattered legal/gate-like checks (Agent B)

Across 14 files, 5 partial implementations exist, none centralized. Coverage map against the plan's 18-gate enumeration:

| Category | Count | Detail |
|---|---|---|
| Completely missing | 11 | G01, G02, G04, G06, G07, G11, G12, G13, G16, G17, G18 |
| Partial / scattered | 4 | G03, G08, G09, G10 |
| Phase 4 (intentional) | 1 | G07 |

Concrete findings worth carrying forward:
- **Channel-add (`POST /api/channels`) performs zero legal preconditions.** Plan § 3.C says G04+G05+G06 must DECLINE; today a user with no legal_profile and no framework contract can add a channel. (`channels.py:312-446`).
- **Placement-create (`POST /api/placements`) checks reputation block only** (`placements.py:359-363`); no `legal_profile` existence check, no framework-contract check.
- **`get_or_create_framework_contract()` exists** (`contract_service.py:427-444`) but is called from contract listing/generation only — not from channel-add, not from placement-create. The capability is there; the integration is not.
- **G08 ERID is conditional on a feature flag**, not an explicit gate (`publication_service.py:109-120`). `ord_block_publication_without_erid=false` default → silent warning + continue. Once flipped to `true` and a real provider is live, behaviour will be fail-closed; the gate framework should make this deterministic regardless of flag state.
- **S-48 transaction-contract violations:** three direct `session.commit()` calls outside the outermost caller — `channels.py:411-423`, `contracts.py:67`, `contracts.py:134`. These prevent gate injection between service work and commit.
- **BL-037 sub-stage tracking unwired.** `PlacementStatusHistory.metadata_json` JSONB column exists with default `{}` (line 55 of `placement_status_history.py`). Today it records 6 keys (`from_status`, `to_status`, `trigger`, `from_admin_id`, `admin_override_reason`, `correlation_id`). Gate results have no place to land.
- **No dedicated gate exception class.** Errors raised via `ValueError`, `HTTPException(403)`, `PermissionError` — heterogeneous; no `TransitionBlockedError`/`GateBlockedError` for tests/monitoring to catch consistently.

### 1.3 Payout/billing infrastructure + 16.3 residue (Agent C)

**Bot payout flow removal (16.3) empirically verified complete.** Handler directory deleted, `PayoutStates` removed, router unregistered, `__init__.py` import + `__all__` cleaned, regression tests added (`TestNoBotPayoutFlow::test_payout_handler_module_absent`, `test_payout_states_module_absent`). Three entry-point buttons (cabinet, post-completion notification, own_menu) converted to `web_app=portal_webapp("/own/payouts/request")` deeplinks via `src/bot/utils/portal_deeplink.py`. ФЗ-152 principle ("ПД никогда через mini_app/bot") is structurally preserved — the in-flight Telegram exposure path (CRIT-1, BL-045) is gone, not just patched by encryption-at-rest.

**One residue uncertainty:** `mini_app/src/screens/owner/OwnPayoutRequest.tsx` does not exist today, but `CHANGES_2026-04-30_remove-bot-payout-flow.md` describes it as a created placeholder. Either the placeholder was created and removed in a follow-up cleanup (b), never created (a — CHANGES doc aspirational), or `OwnPayouts.tsx` listing screen handles deeplink redirect without a dedicated `/own/payouts/request` route (c). The deeplink target is `/own/payouts/request` — verification needed for whether the route resolves, redirects, or 404s.

**Payout infrastructure for Phase 3 gate prerequisites:**
- Three user-facing endpoints (`/api/payouts/`, `/api/payouts/{id}` GET, POST) all enforce `Depends(get_current_user_from_web_portal)` ✅
- Admin endpoints (`/admin/payouts`, approve/reject) all gated on `AdminUser` web_portal dependency ✅
- `PayoutRequest.requisites` is `EncryptedString(2048)` per 16.2 ✅
- `PayoutRequest.status` enum: `pending`, `processing`, `paid`, `rejected`, `cancelled`
- TODO fields for tax integration already in model: `ndfl_withheld`, `npd_receipt_number`, `npd_receipt_date`, `npd_status`
- Velocity check primitives in `src/constants/payments.py`: `VELOCITY_MAX_RATIO`, `VELOCITY_WINDOW_DAYS`
- S-48 contract: payout services compliant (service owns `async with async_session_factory()`; endpoint receives injected session)

**Gate-relevant absences:**
- **No payout-method enum.** `requisites` is opaque encrypted free-form text (5-512 chars). No `payout_method_type` column; no validation of card PAN vs phone vs account format; no `legal_status ↔ payout_method` matrix.
- **No idempotency keys** on payout operations (status-based idempotency only — weaker than `Transaction.idempotency_key` UNIQUE pattern).
- **No audit_log integration** on admin approve/reject (cross-confirms Agent A's gap on legal_profile mutations — same architectural smell, different surface).
- 17.3 rename: zero impact on payout code (no `credits` references; `balance_rub` and `earned_rub` consistent).

### 1.4 External integrations (Agent D)

Five integration domains, mixed maturity:

| Domain | Status | Phase 3 implication |
|---|---|---|
| **ORD/ERID** | `OrdProvider` Protocol + `StubOrdProvider` production-quality; `YandexOrdProvider` is `NotImplementedError` skeleton | Provider abstraction reusable; production launch waits on contract + credentials |
| **ФНС** | Checksum-only (`fns_validation_service.py`, INN/OGRN/OGRNIP algorithms, ~360 LOC) | Sufficient for G03 smoke check; real `npchk.nalog.ru` API deferred |
| **ЕГРЮЛ/ЕГРИП** | Not integrated; checksum reused from ФНС | G06 must work without snapshot in Phase 3; real snapshot Phase 6 |
| **Мой налог (НПД)** | No API; reminder Celery infrastructure only | G16 must stub in Phase 3; real receipt issuance Phase 4+ |
| **Счёт-фактура** | `InvoiceService` + Jinja2 + WeasyPrint generates HTML/PDF for `legal_entity` ✅; ЭДО skeleton, no Diadoc/СБИС | G17 PDF-only Phase 3; ЭДО submission Phase 4+ |
| **КЭП** | Skeleton in `sign_invoice_with_edo`; deferred per BL-003 | G07 stub returning `phase4_pending`; G15 same |
| **72ч ORD reporting (G12)** | `ord:report_publication` Celery task exists, dispatched at publish; **no Beat scheduling, no `published_at` deadline column on `ord_registration`, no catch-up if task fails post-publish** | Architectural gap — ФЗ-38 critical |

**ORD provider abstraction is the only clean pattern.** Protocol-based with 6 methods, factory selecting Stub vs real from `settings.ord_provider`. Instance-level override possible. Celery tasks (`ord:register_creative`, `ord:report_publication`, `ord:poll_erid_status`) properly queue-routed to `background`, retries configured (3-12 attempts, 300s intervals). Idempotency-by-existence: `register_creative` early-exits if `OrdRegistration.erid` already cached.

**The other four domains are ad-hoc functions, not pluggable.** ФНС is a stateless validation module; ЕГРЮЛ/НПД have no module at all. This is fine for Phase 3 (real implementations deferred) but architectural recommendation is to introduce `FnsProvider`/`NpdProvider`/`EgrulProvider` Protocols even with stub-only implementations, so Phase 4+ integration plugs in cleanly without refactor.

---

## 2. Cross-validation findings

### 2.1 Confirmed (multiple agents converge)

**C-1. Centralized gate framework absent everywhere.** Agent B ran the full gate-coverage map; Agent D verified the file paths from the plan (`src/core/services/{publication,post_publication,agreement,payout}_gates.py`) do not exist. There is no `PlacementGate` enum, no `LegalComplianceService`, no `GateResult` schema, no `GET /api/placements/{id}/gates` endpoint. This is the single largest architectural absence Phase 3 must close.

**C-2. Audit-log gap is cross-cutting, not surface-specific.** Agent A finds zero audit emission on `legal_profile` mutations; Agent C finds zero audit emission on payout admin actions. Treat this as one cross-cutting Phase 3 requirement, not two separate items: the implementation is one helper (`AuditLog.create()` invocation pattern) applied consistently at gate-relevant mutation sites.

**C-3. BL-037 sub-stage tracking unwired despite schema readiness.** Agents B and D both report: `placement_status_history.metadata_json` exists, defaults to `{}`, nullable=False; gate-event recording is the missing application-layer wiring, not a schema change. This means BL-037 is a soft-cost item — JSON shape evolution, not migration.

**C-4. S-48 transaction-contract violations isolated to 3 sites.** Agent B enumerated; Agent C confirmed payout services compliant. Surface area for cleanup is bounded: `channels.py:411-423`, `contracts.py:67`, `contracts.py:134`. Not pervasive — fixable in one focused commit.

**C-5. 16.3 bot-payout-flow removal is structurally complete.** Agent C verified all expected deletions. ФЗ-152 "PII never через bot" is held for the payout domain. **No 16.x leftovers block Phase 3.**

**C-6. PII encryption at rest is consistent across legal_profile and payout.** Agent A confirms `EncryptedString` / `HashableEncryptedString` for sensitive fields; Agent C confirms `requisites` field encrypted; both reference the 16.5b key canonicalization. No fragmentation.

### 2.2 Contradictions (surfaced, not resolved here)

**CON-1. Plan vs code terminology drift — `legal_type` ↔ `legal_status`.**

- Plan (`IMPLEMENTATION_PLAN_ACTIVE.md` § 3.B.1, § 3.B.7, § 3.A): uses `legal_type` consistently with values `(individual, self_employed, ie, llc)`.
- Code (Agent A verified): enum is `legal_status` with values `(individual, individual_entrepreneur, self_employed, legal_entity)`.
- Three of four enum values differ in name (`ie` ≠ `individual_entrepreneur`, `llc` ≠ `legal_entity`); the field name itself differs (`legal_type` ≠ `legal_status`).

Renaming code to match plan would touch 23 fields × ORM/migration/schema/service/FE/repo/tests/snapshots — a destructive multi-day operation. Renaming the plan is documentation-only.

**Recommended resolution (architectural choice resolved per principles, not Marina decision):** rename in plan. Land as a `docs(plan): align legal_type → legal_status terminology` commit BEFORE any Phase 3 implementation commit, so the implementation plan and codebase reference the same vocabulary. This is the alignment-commit pattern from CLAUDE.md "Plan validation gate (c)".

**CON-2. Phase 3 scope ambition for G13-G18.**

Three different positions across artifacts:
- **Agent B (lines 705-712):** "G13-G18 (completion/tax/payout) — blocked by billing rewrite per BL-037" → defer all to Phase 4+.
- **Agent C (lines 543-561):** Phase 3 must include G13-G15 (existing infrastructure); G16-G18 to "Phase 3+ tax integrations, can start Phase 3 with mocks".
- **Agent D (lines 480-490):** Defer G16/G17 to Phase 4+; G18 in Phase 3 only if ORD provider live.

This is a **real product/scope decision for Marina** (D1 in § 5). Per principles ("phasing исходит from dependencies, not preferences"), the right resolution is granular per gate based on what infrastructure exists vs requires net-new external integration:

| Gate | Existing infra | New work needed | Phase 3 verdict |
|---|---|---|---|
| G13 PUBLICATION_PERIOD_ELAPSED | `PlacementRequest.published_at` exists | Date arithmetic | **Phase 3 trivial** |
| G14 ACT_GENERATED | `ActService` + `act_advertiser`/`act_owner` tables | Read existing | **Phase 3 trivial** |
| G15 ACT_SIGNED_BOTH_SIDES | Contract sig schema exists | КЭП integration (BL-003 deferred) | **Phase 3 stub** (`phase4_pending`) |
| G16 TAX_RECEIPT_ISSUED | `payout.npd_receipt_*` columns exist | Real "Мой налог" API | **Phase 3 stub** + Phase 4 real |
| G17 VAT_OBLIGATION_HANDLED | `InvoiceService` HTML/PDF exists | ЭДО submission | **Phase 3 PDF-only gate** + Phase 4 ЭДО |
| G18 PAYOUT_REPORTED_TO_ORD | ORD provider exists if live | Monthly aggregation | **Phase 3 if ORD live** else stub |

This split is the consolidator's recommendation; Marina's call on whether to accept it as written, narrow further, or expand to all-real-implementations.

**CON-3. Phase 3 effort estimate vs realistic scope.**

Plan says 8-10ч. Realistic effort given the consolidated findings: ~30-40ч (see § 7 sequencing). This is not a contradiction between agents — it's a contradiction between the plan's budget and the work it specifies. Resolution: Marina either accepts revised estimate or narrows scope.

**CON-4. `OwnPayoutRequest.tsx` placeholder existence.**

Agent C reports the `.tsx` file does not exist today; `CHANGES_2026-04-30_remove-bot-payout-flow.md` describes it as a created placeholder. This is a doc-vs-reality drift, not an inter-agent contradiction. Surfaced as O.4 (open question — verification cost is small, fix path depends on what verification reveals).

### 2.3 Gaps (not covered by any agent)

**G-1. Consolidated migration plan.** No agent enumerated the FULL set of new columns Phase 3 introduces. Compiled here:
- `legal_profile.fns_verification_status: String(20)` (Agent A)
- `legal_profile.fns_verified_at: DateTime(tz)` (Agent A)
- `legal_profile.egrul_snapshot_at: DateTime(tz)` (Agent A)
- `legal_profile.inn_checksum_valid: Boolean` (Agent A)
- `payout_request.payout_method_type: String(16)` (Agent C, dependent on D2 Marina decision)
- `payout_request.idempotency_key: String + UNIQUE` (Agent C, optional)
- `placement_request.publication_verified: Boolean + default False` (Agent B, for G11)
- `placement_request.publication_verified_at: DateTime(tz)` (Agent B, for G11)
- `ord_registration.published_at: DateTime(tz)` (Agent D, for G12 deadline)
- `ord_registration.deadline_at: DateTime(tz)` (Agent D, computed `published_at + 72h`)

All editable in `0001_initial_schema.py` per pre-prod rule. No new revisions. Existing `placement_status_history.metadata_json` JSONB needs no migration — schema is application-layer (BL-037 wiring is `dict` shape evolution, not DDL).

**G-2. FE consumer chain depth.** Plan § 3.B.5 + § 3.D specify `GET /api/placements/{id}/gates` + `usePlacementGates` hook + remediation URL pattern. No agent details the FE side. Acceptable: Phase 5 work; Phase 3 only commits to the API contract + Pydantic schema + snapshot.

**G-3. Test infrastructure impact.** Agents reference tests at high level. Specific known impacts:
- `tests/integration/conftest.py` — DO NOT TOUCH (project rule).
- `tests/unit/test_contract_schemas.py` snapshots — must regenerate after new fields land via `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py` (per CLAUDE.md procedure).
- `tests/unit/snapshots/legal_profile_response.json` — regenerate (Agent A line 218).
- New `tests/unit/snapshots/gate_result_response.json` — create alongside `GateResult` schema introduction.

**G-4. Mini_app `/own/payouts/request` route resolution.** Verification cost is one grep + one Read of `mini_app/src/App.tsx`; surfaced as O.4 in § 6.

**G-5. ORD provider contract status.** Marina-only info (D3 in § 5).

---

## 3. Architectural assessment

### 3.1 What aligns with principles

**Pluggable provider pattern (ORD).** `OrdProvider` Protocol + `StubOrdProvider` + factory selection by setting + instance-level override is exactly the shape Phase 3+ wants for ФНС/ЕГРЮЛ/Мой налог/ЭДО — reusable as template. Mark this as the canonical example to extend.

**PII encryption layer.** Single master key, canonicalized in 16.5b, applied uniformly via `EncryptedString` / `HashableEncryptedString` across `legal_profile` and `payout_request`. INN's `HashableEncryptedString` + `inn_hash` column for indexed search is the right pattern for searchable PII; reusable if any new compliance fields need search (none currently planned do).

**ФЗ-152 architectural enforcement.** Bot payout flow removal (16.3) is structural, not patch-level. Mini_app `LegalProfileView` is a deliberate redirect placeholder. All payout endpoints + admin endpoints pinned to `web_portal` audience. The principle "ПД never через mini_app/bot" is genuinely held in code today, not just stated as policy.

**S-48 in payout services.** `async with async_session_factory()` ownership pattern in services + injected session in API endpoints is correct.

**`placement_status_history.metadata_json` schema.** JSONB column with default `{}` — application-layer extensibility ready, no DDL needed for BL-037 sub-stage tracking. Choice of JSONB over a typed sub-table is the right pre-production choice (cheap, evolvable).

### 3.2 What is hack-territory (and why)

**G08 ERID is flag-conditional, not a gate.** `if not placement.erid: if settings.ord_block_publication_without_erid and not is_test: raise` (`publication_service.py:109-120`). The conditional bakes the gate's pass/fail into env var state. When the flag is `false` (today's default), the "gate" silently warns and continues. When the flag flips to `true` post-launch, the same code path becomes hard-blocking. This is fragile: gate behaviour should be deterministic per gate definition; production-mode hardness should be a post-decision, not a precondition embedded in the check. Phase 3 must extract the gate definition from the flag, then wrap with production enforcement separately.

**Inline checks scattered across 14 files** with heterogeneous error classes (`ValueError`, `HTTPException(403)`, `PermissionError`, custom). Each service independently loads and validates legal preconditions. The same condition (`legal_profile is not None and legal_profile.is_verified`) is checked in `user_attention_service.py:69-73` (as alert builder) but NOT in `placements.py` or `channels.py` (where it should be a gate). Asymmetric. No single catch path for "gate blocked" in tests/monitoring.

**Three S-48 violations** (`channels.py:411-423`, `contracts.py:67`, `contracts.py:134`). These three sites commit transactions inside services/routers, blocking the gate-injection point that wants to fire BEFORE commit. Each fix is mechanical (move commit to caller), but the framework cannot be cleanly added until these sites are cleaned up first.

**Audit log unused at compliance-critical mutation sites.** `legal_profile` mutations (Agent A) and payout admin actions (Agent C) — both compliance-relevant — bypass `audit_log` entirely. The `audit_log` model accepts `entity_type="legal_profile"` and exists for exactly this purpose; the absence is hooks, not schema.

**`payout_request.requisites` opaque text.** No method enum, no format validation, no `legal_status ↔ payout_method` matrix. G06 cannot pass meaningfully without structure. This is hack-territory because the structure is absent at the schema level (5-512 chars free-form encrypted text), pushing the validation problem to the gate-checker which has no shape to validate against.

### 3.3 What is missing entirely

**The entire 18-gate framework.** No `PlacementGate` enum, no `LegalComplianceService`, no `GateResult` dataclass, no gate-checker modules under `src/core/services/gates/`, no `GET /api/placements/{id}/gates` endpoint, no `usePlacementGates` hook. The plan's § 3.B is a build-from-scratch specification.

**72ч ORD reporting deadline tracking.** `ord:report_publication` Celery task fires synchronously at publish time. No Beat schedule sweeping for breached deadlines. No `published_at` or `deadline_at` columns on `ord_registration`. No catch-up if the dispatch task fails post-publish. ФЗ-38 § 18.1 requires reporting within 72h — this is the highest-stakes legal gap in the consolidated findings.

**Four `legal_profile` compliance fields** (`fns_verification_status`, `fns_verified_at`, `egrul_snapshot_at`, `inn_checksum_valid`).

**Audit-log emission at mutation sites** (legal_profile + payout admin).

**4-6 specialized repository methods** for gate-checkers (per § 3.D plan: `UserRepository.get_with_legal_profile`, `ContractRepository.has_signed_framework`, `LegalProfileRepository.get_verification_status`, `PayoutMethodRepository.get_valid_for_owner`).

**FNS / ЕГРЮЛ / Мой налог / ЭДО real integrations** — but these are intentionally Phase 4+ deferrals, not Phase 3 gaps. Phase 3 needs the Protocol abstractions in place (per § 3.1 architectural recommendation), not the implementations.

---

## 4. Recommendations roadmap

### 4.1 Phase 3 MUST scope (per gate, granular)

Recommendation per principles: build the framework first (3a foundation), then wire gates in dependency order. The 18-gate enum is the contract; per-gate work is incremental implementation behind that contract.

**Cross-cutting (must precede gate implementation):**

- **`PlacementGate` enum** in `src/core/enums/placement_gate.py` — all 18 values, exact strings per Agent B's mapping. This is a one-time commit that fixes vocabulary.
- **`LegalComplianceService`** in `src/core/services/legal_compliance_service.py` — `gates_for_transition(from_status, to_status)`, `check_gate(session, gate, placement)`, `check_gates_for_transition(session, placement, to_status)`. Returns `list[GateResult]`. **Atomic per gate** per BL-037.
- **`GateResult` dataclass** with `gate, passed, blocker, reason_code, remediation_url, remediation_data` (per plan § 3.B.2). Add to `tests/unit/snapshots/` for contract drift guard.
- **6 gate-checker modules** under `src/core/services/gates/` (per plan § 3.B.3): `advertiser_gates.py` (G01-G03), `owner_gates.py` (G04-G06), `agreement_gates.py` (G07 stub), `publication_gates.py` (G08-G10), `post_publication_gates.py` (G11-G12), `payout_gates.py` (G13-G18).
- **BL-037 wiring**: extend `PlacementStatusHistory.metadata_json` JSON shape to include `gate_checks: list[GateResult]` and `sub_stage` / `sub_stage_failed_reason` fields. Wire to `PlacementTransitionService.transition()` so every transition records gate results before/after.
- **`TransitionBlockedError`** custom exception with `blockers: list[GateResult]` field — raised by `PlacementTransitionService` when blocking gates fail. Routers catch + return `400` (or `403` for channel-add precondition) with structured `GateResult[]` body.
- **S-48 cleanup**: move `session.commit()` from `channels.py:411-423`, `contracts.py:67`, `contracts.py:134` to outermost callers.
- **Migration**: add 4 fields to `legal_profile` + 2 to `payout_request` (if D2 method-typing decision goes structured) + 2 to `placement_request` + 2 to `ord_registration`. All in `0001_initial_schema.py`.
- **Repository methods** per § 3.D: `LegalProfileRepository.get_verification_status`, `ContractRepository.has_signed_framework`, `PayoutRepository.get_valid_for_owner` (depends on D2), `LegalProfileRepository.get_expired_snapshots`.
- **Audit log emission helper** + integration at `legal_profile_service` mutations and payout admin approve/reject.

**Per-gate implementations:**

- **G01 ADVERTISER_LEGAL_PROFILE_COMPLETE:** check `user.legal_profile is not None and check_completeness(profile) is True`. Reason code `legal_profile_incomplete`. Remediation `/legal-profile/setup`. Hooks at placement-create (`POST /api/placements`).
- **G02 ADVERTISER_FRAMEWORK_CONTRACT_SIGNED:** wire `contract_service.get_or_create_framework_contract(user_id, role="advertiser")` + check `contract.signed_at is not None`. Reason `framework_contract_unsigned`. Remediation `/contracts/framework/sign`. Hooks at placement-create.
- **G03 ADVERTISER_LEGAL_TYPE_COMPLIANT:** check `legal_profile.legal_status` not null + checksum-validation match (`fns_validation_service.validate_entity_type_match`). Real ФНС API deferred. Reason `legal_status_invalid` / `inn_mismatch`. Hooks at placement-create.
- **G04 OWNER_LEGAL_PROFILE_COMPLETE:** mirror G01 for `current_user` at channel-add. Reason `owner_legal_profile_incomplete`. Remediation portal URL.
- **G05 OWNER_FRAMEWORK_CONTRACT_SIGNED:** mirror G02 for owner role.
- **G06 OWNER_PAYOUT_METHOD_VALID:** depends on D2 Marina decision (method enum vs free-form). If structured: check `payout_request.payout_method_type` valid for `owner.legal_status` per matrix. If free-form: defer real validation, gate returns "method_pending_review" + admin-review path.
- **G07 SUPPLEMENTARY_AGREEMENT_SIGNED:** stub returning `passed=False, blocker=False, reason_code="phase4_pending"`. Plan-explicit.
- **G08 ERID_REGISTERED:** explicit gate replacing flag-conditional check. Pass if `placement.erid is not None` and `ord_registration.status` in (`token_received`, `erir_confirmed`). Production hardness layer (do-not-publish) becomes a separate concern toggleable by `ORD_BLOCK_WITHOUT_ERID`.
- **G09 ORD_CONTRACT_REPORTED:** check `ord_registration.contract_ord_id is not None`. Hooks at escrow → published.
- **G10 PLACEMENT_TEXT_MARKED:** validate ERID marker present in published text per format (`erid: <ERID>` regex).
- **G11 PUBLICATION_VERIFIED:** new field `placement_request.publication_verified`. Set by post-publication verification task (Phase 3 may stub the verification — gate just reads field). If verification deferred, gate stub returns `phase4_pending`.
- **G12 PUBLICATION_REPORTED_TO_ORD:** check `ord_registration.reported_at is not None and reported_at <= published_at + 72h`. **Plus** new Beat task `ord:check_72h_breach` running hourly to retry breached publishes. **Plus** admin alert when breach occurs.
- **G13 PUBLICATION_PERIOD_ELAPSED:** date arithmetic on `placement.published_at + placement.duration`. Trivial.
- **G14 ACT_GENERATED:** check existence of act records for advertiser + owner. Reads existing tables.
- **G15 ACT_SIGNED_BOTH_SIDES:** stub returning `phase4_pending` (КЭП deferred per BL-003).
- **G16 TAX_RECEIPT_ISSUED:** if `owner.legal_status == "self_employed"`, stub returning `phase4_pending` until real "Мой налог" API integrated. If `legal_status` other, pass with `not_applicable`.
- **G17 VAT_OBLIGATION_HANDLED:** if `owner.legal_status == "legal_entity"`, check Invoice generated (PDF-only sufficient for Phase 3 gate). If other, pass with `not_applicable`. ЭДО submission Phase 4+.
- **G18 PAYOUT_REPORTED_TO_ORD:** if ORD provider live AND owner monthly turnover > threshold, check report submitted. If ORD stub, pass with `stub_provider_active` (note in remediation_data). Phase 3 if Marina confirms ORD provider; else stub.

**Cross-cutting integration points:**

- **`PlacementTransitionService.transition()`**: inject `compliance.check_gates_for_transition(...)` at start; raise `TransitionBlockedError(blockers, placement_id)` if blocking gates fail. Admin-override path keeps `transition_admin_override()` per existing pattern + records to `metadata_json.gate_checks` with override flag.
- **`POST /api/channels` channel-add**: hook `compliance.check_gates_for_user_role(user, role="owner")` → if blockers in `{G04, G05, G06}`, raise `ChannelAddDeclinedError(blockers)` → `403 Forbidden` + structured remediation body. **Hard precondition (DECLINE) per plan § 3.B.6.**
- **`POST /api/placements` placement-create**: hook G01/G02/G03 + reputation block. Same pattern.
- **`GET /api/placements/{id}/gates`**: returns `list[GateResult]` for current placement state. UI consumer Phase 5.

### 4.2 Pre-Phase 3 dependencies

**16.x series — already done (verified):**
- 16.1 admin payout web_portal-only ✅
- 16.2 PayoutRequest.requisites encrypted ✅
- 16.3 bot payout flow removed ✅ (Agent C empirical verification)
- 16.5b PII keys canonicalized ✅
- 17.3 credits → balance/funds rename ✅

**No 16.x leftovers block Phase 3.** Earlier note on `OwnPayoutRequest.tsx` placeholder (CON-4) is a doc-vs-reality drift, not a blocker — verification first; if a placeholder needs restoring, that's a 30-line FE patch.

**Plan terminology alignment commit (REQUIRED before implementation begins):**
> `docs(plan): align legal_type → legal_status terminology in IMPLEMENTATION_PLAN_ACTIVE.md § 3`

This is a non-code commit on the feature branch as the first step, per CLAUDE.md "Plan validation gate (c)". It substitutes vocabulary across plan §§ 3.A (Agent A prompt), 3.B.1 (G03), 3.B.3 (legal_type-specific logic in advertiser_gates.py / owner_gates.py / payout_gates.py), 3.B.7 (legal_profile fields). Code stays untouched.

### 4.3 Phase 4 boundary

- **G07** (supplementary agreement signed) — explicit Phase 4 per plan. Phase 3 stubs return `phase4_pending`.
- **G15** (act signed both sides) — depends on КЭП (BL-003 deferred). Stub in Phase 3.
- **G16** (Мой налог real receipt) — Phase 4+. Stub in Phase 3.
- **G17** (счёт-фактура ЭДО submission) — Phase 4+. Phase 3 generates PDF-only via existing `InvoiceService`.
- **КЭП provider decision** (BL-003 unblocking) — needed for Phase 4 G07/G15 implementation. Either КриптоПро contract or SMS-code fallback. Marina decision (D5 in § 5).

The Phase 4 boundary is principled: gates that require external API integrations (Мой налог, Diadoc/СБИС ЭДО, КриптоПро/SMS КЭП) defer until those integrations are real. Phase 3 owns the framework + stub gates so the contract is fixed; Phase 4 swaps stubs for real implementations without touching Phase 3 code.

### 4.4 Phase 5+ boundary

- **Test-mode mock provider pattern** (per CLAUDE.md ERID section: orthogonal to stub provider — mock is for unit tests, stub is for dev/staging end-to-end). Phase 5.
- **Admin runtime override UI for failed gates** (`placement.is_test` admins keeping `pending_gate_resolutions` JSONB) — per plan § 3.B.4. Phase 5 builds UI; Phase 3 stores the data structure correctly.
- **UI Timeline visualization** of all sub-stages (BL-037 admin UI) — Phase 5+.
- **Real ЕГРЮЛ snapshot** (G06 hardening) — per plan reference, Phase 6.

---

## 5. Decision sheet for Marina

### D1. Phase 3 scope width — granular per-gate split

**Context:** CON-2 in § 2.2. Three agents diverged on G13-G18 timing.

**Options:**
- **Narrow:** Phase 3 = G01-G06 + G08 + framework. Defer G09-G18 entirely to Phase 4. Minimum viable compliance.
- **Medium:** Phase 3 = framework + G01-G14 + stub G15/G16/G17 + G18 (if ORD live). Phase 4 swaps stubs for real implementations.
- **Wide:** Phase 3 includes real Мой налог + ЭДО integrations. Effectively merges Phase 4 into Phase 3.

**Recommendation per principles:** medium scope, with the granular per-gate split in § 4.1's table. Reasoning: the gate framework is the architectural durable thing; per-gate implementation is incremental behind a stable contract. Wide scope balloons Phase 3 to ~60-80h with external-contract dependencies; narrow scope leaves the framework underused. Medium gets the framework + most gates + clean Phase 4 boundary for stubs that can't be real yet.

**Why Marina:** scope determines effort estimate (8-10h plan vs 30-40h realistic vs 60-80h wide), drives Phase 4 phasing, and decides which stub gates are acceptable as user-facing in pre-launch.

### D2. Payout method typing for G06

**Context:** Agent C found `payout_request.requisites` is opaque encrypted text. G06 cannot pass meaningfully without structure.

**Options:**
- **(a) Add `payout_method_type: Enum["card", "sbp", "account", "yoo_money"]` column** + per-method format validators + `legal_status ↔ method` matrix per НК РФ.
- **(b) Refactor `requisites` → `requisites_json: JSONB`** with structured method + metadata fields. More flexible, more migration cost.
- **(c) Keep free-form** + G06 returns "method_pending_review" + admin manual review per request.

**Recommendation per principles:** (a). Phase 3 adds method typing as a gate prerequisite. (b) is over-engineered for current UX (single requisites field). (c) defers real validation indefinitely and breaks G06's value proposition.

**Why Marina:** UX impact (FE form needs method selector); НК РФ rules per legal_status (e.g., LLC + card payout has compliance implications) require product confirmation.

### D3. ORD provider contract status

**Context:** Agent D Open Q. Production launch of G08/G09/G10/G12/G18 in real (not stub) mode requires signed contract + API credentials.

**Options:** Yandex / VK / OZON / not yet signed.

**Recommendation per principles:** answer-then-implement. Phase 3 can land with `StubOrdProvider` and `ORD_BLOCK_WITHOUT_ERID=false` — the framework + gates work. The flip to `true` + real provider injection happens at production launch, not Phase 3 merge.

**Why Marina:** product/legal info she owns. Implementation can proceed with stub provider; real provider integration is one-PR scope once credentials arrive.

### D4. КЭП provider decision (BL-003 unblocking)

**Context:** Agents C and D both reference BL-003 deferred indefinitely. G07 + G15 depend on this.

**Options:**
- **(a) Sign КриптоПро contract** + integrate qualified electronic signature.
- **(b) SMS-code fallback** per existing BL-003 `signature_method=sms_code` deferred option.
- **(c) Defer to Phase 4** — Phase 3 stubs G07/G15 with `phase4_pending`.

**Recommendation per principles:** (c) for Phase 3, (a) or (b) decided before Phase 4 implementation begins. Phase 3 should not block on a contract or workflow decision when the framework can ship with stubs.

**Why Marina:** legal/contract decision; business workflow (К ЭП vs SMS UX) is Marina's call.

### D5. `OwnPayoutRequest.tsx` placeholder verification

**Context:** CON-4 + GAP-4. Doc says placeholder created; current state shows file absent.

**Options:**
- **(a) Restore placeholder** per CHANGES_2026-04-30 description (`<OpenInWebPortal target="/own/payouts/request"/>`).
- **(b) Document expected behavior** (deeplink lands at `/own/payouts` listing, not at request screen).
- **(c) Verify route handler in `mini_app/src/App.tsx`** before deciding.

**Recommendation per principles:** start with (c) — verification is one Read of `App.tsx`. If route is missing → (a). If route redirects → (b) document.

**Why Marina:** UX impact small, but tap → 404 is a regression worth not shipping.

---

## 6. Open questions

These are unresolvable without Implementation session deep dive (architectural ambiguities Marina/Implementation needs to resolve via empirical work, not product decision).

**O.1 BL-037 metadata JSON shape evolution policy.** As gates land per phase, the `metadata_json.gate_checks` shape grows. Strategy options: (i) accumulate freely with `gate_id` keys, (ii) version the shape via `metadata_schema_version` field, (iii) snapshot per-gate via separate JSONB key. Decision is implementation-time; pick when wiring transition service.

**O.2 `placement.is_test` admin pause vs blocker semantics.** Plan § 3.B.4 says admin override stores blockers in `placement.pending_gate_resolutions` JSONB without raising. Today no `pending_gate_resolutions` column exists. Choice: add column or reuse `metadata_json.pending_gate_resolutions` sub-key. Implementation-time decision.

**O.3 Test placement-vs-real-placement gate semantics.** Real placements: blocking gate raises. Test placements: blocking gate stores + transition proceeds. Edge case: test placement that becomes real (`is_test` flipped). Implementation should specify behavior — block at flip with all stored unresolved gates, or allow flip + raise on next transition.

**O.4 `mini_app /own/payouts/request` route resolution** (also D5 in decision sheet — tracked in both because verification is small + UX call needed if route missing).

**O.5 `velocity` checks integration with G06.** Agent C noted `VELOCITY_MAX_RATIO` / `VELOCITY_WINDOW_DAYS` constants imported but logic outside audit scope. Velocity check feels like an anti-fraud gate (G06-adjacent) but is not in the 18-gate enum. Either fold into G06 reasoning or document as separate non-legal precondition.

**O.6 Gate execution ordering when multiple blockers fail.** When G01 + G02 both fail at placement-create, plan implies `list[blockers]` returned. Acceptance: do all gates run unconditionally and collect, or short-circuit at first blocker for performance? Plan § 3.B.2 implies collection; implementation should confirm.

---

## 7. Implementation sequencing recommendation

Recommended split into 4 sub-sprints under `feature/legal-compliance-gates` branch. Each sub-sprint is a coherent commit boundary with its own CHANGES doc per project convention. Total realistic effort ~30-40h (vs plan estimate 8-10h). If Marina narrows scope per D1, drop bottom sub-sprints accordingly.

### Phase 3a — Foundation (~12-15h)

1. **First commit on branch:** `docs(plan): align legal_type → legal_status terminology` per § 4.2 (CLAUDE.md plan validation gate).
2. **Migration:** edit `0001_initial_schema.py` directly. Add 4 fields to `legal_profile`, 2 to `placement_request`, 2 to `ord_registration`, `payout_method_type` to `payout_request` if D2 = (a). Reset DB + `alembic upgrade head` + `alembic check`.
3. **`PlacementGate` enum** (`src/core/enums/placement_gate.py`) — 18 string values.
4. **`GateResult` dataclass** + Pydantic schema + snapshot in `tests/unit/snapshots/gate_result_response.json`.
5. **`LegalComplianceService`** skeleton + `gates_for_transition()` static map (status pair → `list[PlacementGate]`).
6. **Six gate-checker module skeletons** under `src/core/services/gates/` — empty `check()` functions returning `passed=False, reason_code="not_implemented"`.
7. **Repository methods** per § 3.D: `LegalProfileRepository.get_verification_status`, `ContractRepository.has_signed_framework`, etc.
8. **Audit log helper** `_log_compliance_mutation()` + integration at `legal_profile_service.create_profile/update_profile/upload_scan` and payout admin `approve_request/reject_request`.
9. **S-48 cleanup:** move `session.commit()` from 3 violation sites to outermost callers.
10. **`TransitionBlockedError` + `ChannelAddDeclinedError`** custom exceptions.
11. **CHANGES** + lint/typecheck pass.

### Phase 3b — Gate implementation (~10-15h, scope per D1)

Implement per-gate per § 4.1. Order suggestion (dependency-driven):
- G01-G03 (advertiser preconditions, placement-create hook).
- G04-G06 (owner preconditions, channel-add hook with DECLINE).
- G07 stub (`phase4_pending`).
- G08 explicit gate (decoupled from `ORD_BLOCK_WITHOUT_ERID` flag — gate determines pass/fail; flag determines whether failed gate raises at publish).
- G09-G10 (ORD contract reported, ad text marked).
- G11-G12 + 72ч Beat task (`ord:check_72h_breach`) + admin alert.
- G13-G14 (date arithmetic + act presence).
- G15-G17 stubs.
- G18 stub or real per D3.

Each gate gets unit tests; happy-path + blocker-path. Integration tests at transition boundaries.

### Phase 3c — Integration (~5-8h)

12. **`PlacementTransitionService.transition()`** integration: call `compliance.check_gates_for_transition()` at start; raise `TransitionBlockedError` on blockers; record `metadata_json.gate_checks` either way.
13. **Channel-add hook** in `POST /api/channels` — call `compliance.check_gates_for_user_role(user, "owner")` for `{G04, G05, G06}`; raise `ChannelAddDeclinedError` (HTTP 403 + structured body).
14. **Placement-create hook** in `POST /api/placements` — call advertiser gates `{G01, G02, G03}`; raise `400` with structured body.
15. **Admin override path** `transition_admin_override()` — store `metadata_json.gate_checks` with `override=True` flag + `pending_gate_resolutions` for test placements.

### Phase 3d — API + acceptance (~3-5h)

16. **`GET /api/placements/{id}/gates`** endpoint returning `list[GateResult]`.
17. **Snapshot test** for `GateResult` shape (regenerate `gate_result_response.json`).
18. **Acceptance scenarios** per plan § 3.C — 7 integration tests covering legal_type matrix.
19. **CHANGES** + CHANGELOG `[Unreleased]` update.

### Verification gate per CLAUDE.md "Process discipline"

- Local `make ci-local` passes against develop baseline (76 failed / 780 passed pytest, 20 ruff errors). Phase 3 must not regress; new tests count toward `passed`.
- `alembic check` returns "No new upgrade operations detected" after migration edit.
- `tests/unit/test_contract_schemas.py` snapshots regenerated for `LegalProfileResponse` (with new fields), `GateResult` schema (new), `PlacementResponse` if any new transition metadata leaks into it.

---

## Source artifact line counts

- Agent A: 412 lines (21.8 KB)
- Agent B: 791 lines (29.0 KB)
- Agent C: 619 lines (28.3 KB)
- Agent D: 582 lines (27.1 KB)
- **Total source:** 2 404 lines / 106.2 KB across 4 read-only research artifacts.

🔍 Verified against: develop @ `7ae137c` | 📅 Compiled: 2026-05-02
