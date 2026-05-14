# CHANGES — Phase 4 Supplementary Agreements (ДС)

**Date:** 2026-05-14
**Branch:** feature/supplementary-agreements
**Base:** develop @ 1327fb9
**Target:** v0.8.0 on main
**Span:** PROMPT 26 → 27 → 28 → 28b probe → 29 closure
**Plan reference:** IMPLEMENTATION_PLAN_ACTIVE.md § Phase 4

---

## Scope summary

Phase 4 of legal compliance gate system — Supplementary Agreements (ДС) flow.

Per placement, two Contract rows with `contract_type='supplementary_agreement'` are generated
on owner approval (BEFORE `→ pending_payment` transition per Q-A.1 Option 1). Both parties sign
via existing `/api/contracts/{id}/sign` endpoint. G07_SUPPLEMENTARY_AGREEMENT_SIGNED gate body
wired to check `exists_signed_supplementary_both_sides(placement_id)`. ContractEvent audit
table records BL-037 sub-stages (generated → notified → signed → activated).

G15/G16 explicitly deferred to Phase 5 per D1 (code comments в `payout_gates.py` +
`legal_compliance_service.py` already labelled them payout-side / Phase 5 territory).

---

## Per-step detail (12 commits + 1 closure refactor)

### Step 0: docs(phase-4): align plan with research findings (3e05d67)
- `IMPLEMENTATION_PLAN_ACTIVE.md` updated с D1/D2/D3 locks + Q-A.x/Q-B.x/Q-M.x decisions

### Step 0a: refactor(templates): extract shared partials for contracts/acts (DRY) (5e0c600)
- Extracted `_partials/contract_css.html`, `_partials/contract_header.html`
- (`_partials/contract_signatures.html` dropped — existing 6 contract templates inline sigs; not shared pattern. BL-111 candidate)
- 11 existing contract/act templates refactored to `{% include %}`
- Per Q-M.1 decision — prevent 16 CSS duplications когда ДС adds 5 templates

### Step 1: feat(model): supplementary agreement extensions to Contract + new ContractEvent table (0e6ef5b)
- D2: `Contract.placement_request_id` → `placement_id` rename
- New: `Contract.parent_contract_id` SELF-FK ON DELETE SET NULL
- New: composite `ix_contract_placement_type` index
- New: partial UNIQUE `uq_contracts_supplementary_placement_role` (Q-B.6 idempotency)
- New: `ContractEvent` audit table (Q-A.2 — supersedes plan's `contract.metadata_json` claim)
- `ContractType` enum: added `supplementary_agreement` value
- Pre-prod migration: `0001_initial_schema.py` edited (BL-061 exception)

### Step 2: feat(repo): ДС query methods + ContractEvent recorder helper (4ed9a2d)
- 4 net-new methods (Q-A.5):
  - `list_supplementary_for_placement(placement_id)`
  - `get_by_placement_and_role(placement_id, role)`
  - `count_unsigned_supplementary_for_user(user_id)`
  - `exists_signed_supplementary_both_sides(placement_id)` — G07 backing
- `record_event()` helper for ContractEvent audit
- S-48: flush-only, no commits

### Step 3: refactor(api): rename placement_request_id → placement_id in Contract surface (D2 closure) (25d029d)
- Router, ContractService param, web_portal types, integration tests, snapshot regen
- Other models (`OrdRegistration`, `Transaction`, `Act`, `Review`, `PlacementDispute`) untouched — separate FKs

### Step 4: feat(service): SupplementaryAgreementService + PublicationFormat + ContractEvent schemas (fc4d6e3)
- `SupplementaryAgreementService`: instance shape (Q-B.1), S-48 Pattern 1
- `generate_for_placement()` — idempotent, race-safe via IntegrityError catch
- `_select_template(role, legal_status)` helper (Q-B.2 — NOT `_CONTRACT_TEMPLATE_MAP` extension)
- `_build_placement_ctx()` helper (Q-B.4) reusing `_build_fee_context`
- `ContractEvent` Pydantic discriminator schemas (closed Literal `event_type`)
- `PublicationFormat.label()` + `.duration_hours()` classmethods (Q-M.2) — single source of truth
- Notification dispatch: Celery `apply_async` mirror `placement_request_service.py:309`

### Step 5: feat(templates): 5 supplementary agreement templates + smoke tests (df14ac2)
- `supplementary_agreement_advertiser.html` (single, inline legal_status conditionals)
- `supplementary_agreement_owner_{individual,self_employed,ie,le}.html` (4 per-legal_status files)
- erid: Q-M.4 placeholder "присваивается при регистрации в ОРД перед публикацией"
- New partials extracted: `sup_agreement_financial_table.html` + `sup_agreement_placement_details.html`
- Smoke tests: `_select_template` routing + render-no-error

### Step 6: feat(handlers): trigger ДС generation on owner approval / advertiser counter-accept (7b49f06)
- 4 caller sites integrated (Q-A.1 + Q-A.3):
  - `src/bot/handlers/owner/arbitration.py`
  - `src/bot/handlers/advertiser/campaigns.py`
  - `src/api/routers/campaigns.py` (Pattern 2 self-contained)
  - `src/tasks/notification_tasks.py` (periodic — per-placement transactional isolation)
- Mirror `publication_service.py:494-505` act pattern
- ДС generated BEFORE transition attempt; G07 surfaces "ДС создано, подпишите" via existing `TransitionBlockedError` handlers

### Step 7: feat(gates): wire real G07 body (supplementary signed both sides) (d72d186)
- `G07_SUPPLEMENTARY_AGREEMENT_SIGNED` real body: pure-read via `repo.exists_signed_supplementary_both_sides`
- New `GateReason.SUPPLEMENTARY_NOT_SIGNED` (Q-M.3) — distinct from `PHASE4_PENDING` marker
- Dropped stale "МES Acts API" docstring (D3)
- Periodic task discriminator updated для new reason_code
- 3 unit tests: both signed pass, partial fail, no-ДС fail

### Step 8: feat(api): GET /api/placements/{id}/supplementary-agreements + sign event emission (dc84bb0)
- New endpoint: web_portal JWT, participant permission (advertiser OR owner), 403/404 handling
- `SupplementaryAgreementResponse` schema: `{advertiser, owner, both_signed}`
- `ContractService.sign_contract()` now emits `supplementary_signed` ContractEvent for supplementary `contract_type`
- Auto-emits `supplementary_activated` when both sides reach signed status
- mini_app: NOT touched (ФЗ-152)

### Step 9: feat(web): supplementary agreement UI on CampaignWaiting + OwnRequestDetail (web_portal only) (c40d1e3)
- `web_portal/src/api/contracts.ts`: `getSupplementaryForPlacement()`
- `web_portal/src/hooks/useSupplementaryAgreement.ts`: React Query polling
- `CampaignWaiting.tsx`: advertiser-side ДС section
- `OwnRequestDetail.tsx`: owner-side ДС section
- Reuses existing `useSignContract` hook
- mini_app: 0 references (grep verified)

### Step 10: test(phase-4): unit + integration + Playwright for ДС flow (6810999)
- Unit: `SupplementaryAgreementService` (idempotency, race, framework prereqs, ContractEvent recording)
- Unit: endpoint permission (403 non-participant, 404 missing)
- Integration: full e2e (owner approve → 2 ДС generated → both sign → G07 pass → transition)
- Playwright: `sign-supplementary-agreement.spec.ts` (3 viewports, smoke-level — BL-112 для full interactive с seed fixture)

### Step 11.0: refactor(api): extract contract_to_response helper to shared module (этого prompt — a6dc462)
- Cleanup PROMPT 28 surprise: private cross-router import → public `src/api/helpers/contract_response.py`
- New `src/api/helpers/` subdir + `__init__.py` package marker
- 4 contracts.py callsites updated; 2 placements.py callsites updated; 3 now-unused imports dropped (`Contract`, `ContractStatus`, `SignatureMethod`)
- No behavior change

---

## Surprises log (consolidated across PROMPT 26-28)

### PROMPT 26
1. **Template count drift:** research artifact had typo (Agent B "5 files" but enumerated 6). Reality 6+6=12. No code action.
2. **Second migration file** `e6a88faa9fa0_*` (Phase 2 `placement_status_history`) exists despite CLAUDE.md "1 consolidated migration" claim. → **BL-110 candidate** (CLAUDE.md update).
3. Side fixes within partials commit: `act_placement.html box-info → box-ok` semantic class rename + `owner_service_legal_entity.html .platform-name → .pname` canonicalization. Per principles, accepted.
4. Test count drift baseline 1033 → 1050 (+17 pre-existing tests between research date 2026-05-13 and execution 2026-05-14).

### PROMPT 27
1. `_partials/contract_signatures.html` not extracted in Step 0a (signature blocks inline в existing 6 contract templates, not shared pattern). Agent created 2 different partials instead (`financial_table` + `placement_details`). → **BL-111 candidate** (optional, low priority).
2. `PublicationFormat` enum lives в `src/db/models/placement_request.py` (not in `src/core/enums/publication_format.py` as prompt assumed). L75 verified empirically.
3. Test fixture updates в 3 handler/task test files (mock `SupplementaryAgreementService` — required by Step 6 hook).
4. Bundled side-fixes: `ContractEvent` docstring `ds_generated_advertiser` → canonical `supplementary_*`. `legal_compliance_service.py:77` "МES Acts API" comment drop (D3 opportunistic).
5. Stop-hook BL-013 fires 3x for missing CHANGES — acked 2 per BL-016, silent-ignore identical. → **BL-113 candidate** (hook deferred bundle detection).

### PROMPT 28
1. `_contract_to_response` cross-router private import (Step 8.2) — resolved Step 11.0 этого prompt.
2. Step 10 integration test seed: `_seed_phase4_setup` seeds both sides with `contract_type='advertiser_framework'` — initially suspected `get_framework_contract` bug, **PROMPT 28b probe confirmed NO BUG** — `advertiser_framework` is umbrella `contract_type` with `Contract.role` discriminator (intentional, L18-deferred-cleanup). Audit: `tmp/contract_repo_framework_audit_2026-05-14.md`. → **BL-115 candidate** (umbrella rename `advertiser_framework` → `framework`, ~12 files, dedicated PR).
3. Playwright spec scoped to smoke (seed fixture для full interactive не существует в `scripts/e2e/seed_e2e.py`). → **BL-112 candidate** (Playwright full E2E seed fixture).
4. Stop-hook noise — same BL-013 hook fires 12+ times. → **BL-113 candidate confirmed**.

### PROMPT 28b probe
- Read-only verification of `ContractRepo.get_framework_contract(user_id, role)`. Verdict: **NO BUG**. Symmetric read/write paths use `contract_type='advertiser_framework'` as umbrella name; `Contract.role` discriminator distinguishes owner/advertiser sides. Existing docstrings в G02/G05 gate bodies already document L18 deferred-cleanup. No action required Phase 4.

---

## BL candidates surfaced (NOT committed to BACKLOG.md — accumulate для production launch closure batch)

| ID | Title | Priority | Source |
|----|-------|----------|--------|
| BL-110 | CLAUDE.md migration count claim outdated ("1 consolidated" vs reality 2 files post-Phase 2) | low | PROMPT 26 |
| BL-111 | `_partials/contract_signatures.html` dropped from Step 0a refactor — existing 6 contracts inline sigs (not shared) | low | PROMPT 27 |
| BL-112 | Playwright `sign-supplementary-agreement` seed fixture creation in `scripts/e2e/seed_e2e.py` (smoke → full interactive) | medium | PROMPT 28 |
| BL-113 | Stop-hook BL-013 deferred bundle detection (12+ identical fires when CHANGES legitimately deferred) | low | PROMPT 28 |
| BL-115 | `"advertiser_framework"` → `"framework"` umbrella `contract_type` rename (~12 files, dedicated cleanup PR) | low | PROMPT 28b probe / G02 G05 docstring L18 |

(BL-114 reserved for `get_framework_contract` framework filtering bug — RESOLVED as NO BUG per probe; ID retired/skipped.)

---

## Deferred to production launch

- **BL-079** dependency: campaign media upload + object storage (for Yandex ORD `mediaData.mediaUrl`) — required для real production ORD registration; placement images currently `file_id` Telegram-only
- **BL-107** (channel registration ≥10k subscribers verification ФЗ-303) — launch-blocking
- **BL-105** (ККТУ codes UI integration — Yandex ORD v7 from 07.11.2025)
- **BL-104 strategic:** Telegram→MAX migration plan (ФЗ-72 запрет рекламы в Telegram с 01.01.2027)
- **ДС sub-stages `supplementary_notified`** currently emit on Step 4 service path — verify production notification dispatch path matches Celery worker registration (Phase 5 admin override может intercept)
- **Q-M.4 carve-out:** ДС templates render erid placeholder. Post-escrow erid generation registers с ОРД but ДС contract text не regenerated (per legal — signed document immutable). Consider audit trail для tracking which erid was assigned per ДС (BL candidate post-MVP).

---

## Verification artifacts

- `tmp/phase4_research_summary_2026-05-13.md` — consolidated research
- `tmp/phase4_research_agent_a_2026-05-13.md` — Agent A detail
- `tmp/phase4_research_agent_b_2026-05-13.md` — Agent B detail
- `tmp/phase4_probe_state_2026-05-13.md` — initial probe
- `tmp/phase4_step4_notification_pattern.md` — PROMPT 27 dispatch decision
- `tmp/phase4_step6_cilocal_v2.txt` — PROMPT 27 Step 6 ci-local
- `tmp/phase4_step7_cilocal.txt` — PROMPT 27 Step 7 ci-local
- `tmp/phase4_step8_router_audit.md` — PROMPT 28 endpoint placement decision
- `tmp/phase4_step9_fe_audit.md` — PROMPT 28 frontend audit
- `tmp/phase4_step8_cilocal.txt` — PROMPT 28 Step 8 mid ci-local
- `tmp/phase4_step10_cilocal.txt` — PROMPT 28 Step 10 final ci-local
- `tmp/contract_repo_framework_audit_2026-05-14.md` — PROMPT 28b probe verdict
- `tmp/phase4_step11_helper_audit.md` — этого prompt Step 11.0 helper location decision

---

## Gate baseline (post-merge to main, pre-tag)

| Gate | Baseline before Phase 4 | Final |
|------|------------------------|-------|
| make format-check | 0 errors / 405 files | 0 errors / 416 files |
| make lint | 7 errors (BL-024) | 7 errors (BL-024 preserved) |
| make typecheck | 0 errors / 294 src | 0 errors / 300 src |
| make ci-local pytest | 1033 passed | 1087 passed (+54 net) |
| Frontend lint | 2 errors + 6 warnings (BL-024) | 2 + 6 (BL-024 preserved) |
| Frontend tsc | 0 errors | 0 errors |

---

## Commits (12 + 1 closure refactor + 1 docs)

```
<SHA>  docs(phase-4): closure CHANGES + CHANGELOG (этого commit)
a6dc462 refactor(api): extract contract_to_response helper to shared module
6810999 test(phase-4): unit + integration + Playwright for ДС flow
c40d1e3 feat(web): supplementary agreement UI on CampaignWaiting + OwnRequestDetail (web_portal only)
dc84bb0 feat(api): GET /api/placements/{id}/supplementary-agreements + sign event emission
d72d186 feat(gates): wire real G07 body (supplementary signed both sides)
7b49f06 feat(handlers): trigger ДС generation on owner approval / advertiser counter-accept
df14ac2 feat(templates): 5 supplementary agreement templates + smoke tests
fc4d6e3 feat(service): SupplementaryAgreementService + PublicationFormat helpers + ContractEvent schemas
25d029d refactor(api): rename placement_request_id → placement_id in Contract surface (D2 closure)
4ed9a2d feat(repo): ДС query methods + ContractEvent recorder helper
0e6ef5b feat(model): supplementary agreement extensions to Contract + new ContractEvent table
5e0c600 refactor(templates): extract shared partials for contracts/acts (DRY)
3e05d67 docs(phase-4): align plan with research findings
```

🔍 Verified against: `feature/supplementary-agreements @ a6dc462` (pre-docs-commit state)
📅 Generated: 2026-05-14 Phase 4 closure
