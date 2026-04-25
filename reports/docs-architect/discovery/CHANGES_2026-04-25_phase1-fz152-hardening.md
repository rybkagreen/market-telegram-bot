# CHANGES 2026-04-25 — Phase 1: ФЗ-152 hardening + mini_app legal strip

## Scope

Phase 1 of the production-readiness consolidation plan
(`IMPLEMENTATION_PLAN_ACTIVE.md`). Closes the FZ-152 (защита персональных
данных) compliance loop: ПД flows live only in `web_portal`, mini_app
reaches them via the `OpenInWebPortal` bridge built on Phase 0's
ticket-exchange endpoints.

## Phase 1 commits (in order on `feature/fz152-legal-hardening`)

| Commit | Type | Subject |
|--------|------|---------|
| edc1a09 | docs | align plan + CLAUDE.md with PF.2/PF.4 decisions |
| 04c480b | fix(api) | legacy aud-less JWT → 426 + WWW-Authenticate (PF.2) |
| 034e8bc | refactor(api) | audit middleware reads request.state instead of re-decoding JWT (PF.4) |
| 0f8f065 | feat(api) | switch 23 PII endpoints to web_portal-only auth (§1.B.1) |
| 3ada945 | feat(api) | remove dead POST /api/users/skip-legal-prompt (§1.B.5) |
| 110289c | feat(api) | e2e-login accepts source param for web_portal JWT minting (§1.B.6) |
| 5cd83f5 | docs | research consolidation 1.A (4 areas + objections) |
| 80e7413 | feat(bridge) | TicketLogin + OpenInWebPortal infrastructure (§1.B.3) |
| 6b8e9b9 | feat(api) | carve out accept-rules to legal_acceptance router (§1.B.2 A.2) |
| 6b858ad | feat(mini-app) | carve out accept-rules + 4 PII screens to portal redirect (§1.B.2 step 1/3) |
| cd91be4 | feat(mini-app) | Cabinet + MainMenu use OpenInWebPortal for legal entries (§1.B.2 step 2/3) |
| 0388637 | feat(mini-app) | heavy strip — delete PII screens, hooks, api, types (§1.B.2 step 3/3) |
| ebbc7f0 | chore(phase-1) | forbidden-pattern guards + backlog tickets + CHANGELOG (§1.D) |
| e415ebf | fix(mini-app) | restore non-PII OrdRegistration/OrdStatus types |

14 commits. Net: ≈ 1500 LOC removed (mini_app PII surface), ≈ 200 LOC
added (bridge UI + carve-out + safeRedirect + scope-policy docs).

## Pre-flight verifications consumed in this phase

- **PF.1** (mypy baseline) — passed at Phase 0 close; baseline 10
  errors / 5 files / 272 source files frozen at `1fd0960`. Phase 1 mypy
  result: identical roster, 273 source files (+1 = `legal_acceptance.py`).
  **Zero new errors in Phase 1 surface.**
- **PF.2** (legacy JWT 401 vs 426) — implemented in §1.B.0a (426 +
  `WWW-Authenticate` header).
- **PF.3** (bridge happy-path) — test from Phase 0 follow-up still
  green; step 4 extended with `request.state.user_id` / `user_aud`
  assertion in §1.B.0b.
- **PF.4** (audit middleware refactor) — implemented in §1.B.0b. ~21
  LOC across 2 files; PF threshold respected.
- **V1** (6 target portal screens exist) — confirmed.
- **V2** (skip-legal-prompt unused) — 0 hits across 14 days of
  nginx/api logs; removed in §1.B.5.
- **V3** (useMe via ky beforeRequest) — confirmed token flows through
  localStorage automatically.
- **V4** (accept-rules provably non-PII) — `AcceptRulesRequest` =
  two booleans; service writes timestamps + constant
  `signature_method`. Carve-out justified.
- **V5** (mini_app aud passes get_current_user) — confirmed by
  existing `test_case1_*`.

## Affected files

### §1.B.0a — Legacy JWT 426 flip (PF.2)
- `src/api/dependencies.py`: `MissingRequiredClaimError` branch flips
  `HTTP_401_UNAUTHORIZED` → `HTTP_426_UPGRADE_REQUIRED`; adds
  `headers={"WWW-Authenticate": "Bearer"}`.
- `tests/unit/api/test_jwt_aud_claim.py::test_case3_*` updated
  assertion + header check; renamed `_401` → `_426`.

### §1.B.0b — Audit middleware refactor (PF.4)
- `src/api/dependencies.py`:
  - `_resolve_user_for_audience` accepts `request: Request | None`,
    sets `request.state.user_id` + `user_aud` on success.
  - Three public deps (`get_current_user`,
    `get_current_user_from_web_portal`,
    `get_current_user_from_mini_app`) take `request: Request` as first
    parameter (auto-injected by FastAPI).
- `src/api/middleware/audit_middleware.py`:
  - `_extract_user_id_from_token` helper deleted (unsigned-JWT decode
    code smell from Phase 0).
  - `dispatch` reads `getattr(request.state, "user_id", None)` and
    adds `aud` claim to the audit-log `extra` dict.
  - `/api/acts/*` added to `_SENSITIVE_PREFIXES`.
- New unit cases in `tests/unit/api/test_jwt_aud_claim.py` verify the
  `request.state` write contract.
- `tests/integration/test_ticket_bridge_e2e.py` step 4 extended.
- `CLAUDE.md` — `audit_middleware.py` removed from NEVER TOUCH list.

### §1.B.1 — 23 PII endpoints → web_portal-only auth
- `src/api/routers/legal_profile.py` (7 endpoints)
- `src/api/routers/contracts.py` (7 endpoints)
- `src/api/routers/acts.py` (4 endpoints)
- `src/api/routers/document_validation.py` (5 endpoints)

All `Depends(get_current_user)` → `Depends(get_current_user_from_web_portal)`.
`tests/integration/test_api_legal_profile.py` fixture override updated.

### §1.B.2 — Mini_app legal strip (heavy + carve-out)

**Carve-out:** `POST /api/contracts/accept-rules` is provably non-PII
(2 booleans in, timestamps out). Routing it through web_portal-only
would force every new mini_app user to bounce through the browser for a
flag-set. Resolved by moving the endpoint to a separate router with
`get_current_user` (both audiences); URL preserved.

- New: `src/api/routers/legal_acceptance.py`. Single endpoint, ~70 LOC
  including the FZ-152 scope-policy docstring.
- `src/api/routers/contracts.py` — `accept_rules` handler removed,
  `AcceptRulesRequest` import removed.
- `src/api/main.py` — register `legal_acceptance_router`.

**Mini_app deletions (20 files):**
- 5 PII screens + `.module.css`: LegalProfileSetup, LegalProfilePrompt,
  ContractDetail, ContractList, MyActsScreen.
- 4 components: KepWarning, ContractCard, TaxBreakdown, LegalStatusSelector.
- 2 api modules: api/legalProfile.ts, api/contracts.ts.
- 2 hook files: useLegalProfileQueries.ts, useContractQueries.ts.
- 1 store: legalProfileStore.ts.

**Mini_app placeholders (4 screens):**
- `AdvertiserFrameworkContract.tsx` → portal `/contracts/framework`
- `OwnPayoutRequest.tsx` → portal `/own/payouts/request`
- `CampaignPayment.tsx` → portal `/adv/campaigns/:id/payment`
- `LegalProfileView.tsx` → portal `/legal-profile/view`

**Mini_app new (carve-out):**
- `mini_app/src/api/legal-acceptance.ts`
- `mini_app/src/hooks/useLegalAcceptance.ts`

**Mini_app refactored:**
- `Cabinet.tsx`: `useMyLegalProfile`/`useContracts` removed; legal-profile
  + contracts entries use `useOpenInWebPortal`.
- `MainMenu.tsx`: legal banner CTA uses `useOpenInWebPortal`.
- `AcceptRules.tsx`: switches import to `useLegalAcceptance`;
  redirect target changed (`/legal-profile-prompt` deleted).
- `App.tsx`: 5 lazy imports + 5 routes removed (legal-profile-prompt,
  legal-profile, contracts, contracts/:id, acts).

**Types pruned from `mini_app/src/lib/types.ts` (11):**
LegalStatus, TaxRegime, ContractType, ContractRole,
ContractSignatureInfo, ContractStatus, SignatureMethod, LegalProfile,
LegalProfileCreate, Contract, RequiredFields. (`OrdRegistration`,
`OrdStatus` retained — non-PII placement registration metadata.)

### §1.B.3 — Bridge UI

**Web_portal:**
- `web_portal/src/screens/auth/TicketLogin.tsx` (new, with `safeRedirect`).
- `web_portal/src/api/auth.ts` — append `consumeTicket` + `AuthTokenResponse`.
- `web_portal/src/hooks/useConsumeTicket.ts` (new).
- `web_portal/src/App.tsx` — route `/login/ticket` registered.

**Mini_app:**
- `mini_app/src/components/OpenInWebPortal.tsx` (new).
- `mini_app/src/hooks/useOpenInWebPortal.ts` (new).
- `mini_app/src/api/auth.ts` — append `exchangeMiniappToPortal` + `TicketResponse`.

**Security:** `safeRedirect()` in TicketLogin allowlists same-origin
paths starting with single `/`. Open-redirect mitigation per
PHASE1_RESEARCH §1.A.3 objection — mandatory, not optional.

### §1.B.5 — Dead-code removal
- `src/api/routers/users.py` — `skip_legal_prompt` handler + unused
  imports removed.
- `tests/integration/test_web_portal.sh` — corresponding 401-no-token
  smoke removed.

### §1.B.6 — Test infrastructure (a)
- `src/api/routers/auth_e2e.py` — `E2ELoginRequest.source: JwtSource = "mini_app"`,
  `E2ELoginResponse.source` field. Default keeps existing `global-setup.ts`
  working; specs needing web_portal token pass `source="web_portal"`.

(Playwright specs themselves — `legal-profile-requires-web-portal.spec.ts`,
`ticket-login.spec.ts` — deferred to a follow-up commit on the same
branch BEFORE the merge to develop. *not yet shipped at the time of
this CHANGES write — see "Open items" below.*)

### §1.D — Cross-cutting

- `scripts/check_forbidden_patterns.sh` — three new FZ-152 guards
  (PII identifiers in mini_app/src; deleted routes in App.tsx; PII
  type names in lib/types.ts). Total: 15 checks.
- `reports/docs-architect/BACKLOG.md`:
  - **BL-004** — bake `tests/` into api docker image (deadline Phase 3).
  - **BL-005** — wire `/api/acts/*` to web_portal (deadline Phase 2).
- `IMPLEMENTATION_PLAN_ACTIVE.md` §1.B restructured (§1.B.0a/0b added,
  §1.B.4 superseded, §1.B.5/6 added). Authoritative scope reference
  flipped to `PHASE1_RESEARCH_2026-04-25.md`.
- `CLAUDE.md` NEVER TOUCH list — `audit_middleware.py` removed (PF.4).
- `tests/integration/README.md` — host-pytest documented as canonical.

## Public contracts changed

**Breaking:**
- Aud-less legacy JWT now `426 Upgrade Required` (was `401`). Phase 0
  shipped 401; PF.2 corrected to 426 with reasoning in CHANGELOG.
- 23 endpoints (`/api/legal-profile/*`, `/api/contracts/*` except
  `/accept-rules`, `/api/acts/*`, `/legal-profile/documents/*`) reject
  mini_app JWT with 403.
- `POST /api/users/skip-legal-prompt` removed.

**Additive:**
- `POST /api/auth/consume-ticket` already shipped Phase 0; UI consumer
  added (`TicketLogin`).
- `POST /api/auth/exchange-miniapp-to-portal` already shipped Phase 0;
  UI consumer added (`OpenInWebPortal` + `useOpenInWebPortal`).
- `POST /api/auth/e2e-login` accepts optional `source: JwtSource = "mini_app"`;
  response now carries `source` field.

**Path preserved (carve-out):**
- `POST /api/contracts/accept-rules` URL unchanged but moved to
  `legal_acceptance.py` router; auth dep is `get_current_user` (both
  audiences) instead of `get_current_user_from_web_portal`.

## Acceptance criteria — verified

- [x] `make typecheck` — `Found 10 errors in 5 files (checked 273 source files)`.
      Identical baseline to Phase 0 close (10/5/272); +1 source file = `legal_acceptance.py`.
      **Zero new errors in Phase 1 surface.**
- [x] `poetry run pytest tests/unit/api/ tests/integration/test_api_legal_profile.py
      tests/integration/test_ticket_bridge_e2e.py tests/unit/test_contract_schemas.py`
      — **97/97 passed**.
- [x] `bash scripts/check_forbidden_patterns.sh` — **15/15 passed**.
- [x] `cd mini_app && npm run build` — **clean**.
- [x] Docker smoke (rebuilt nginx + api):
  - `GET /health` → 200 ✅
  - `GET /api/legal-profile/me` with mini_app JWT → **403** ✅
  - `GET /api/legal-profile/me` with legacy aud-less JWT → **426** + `WWW-Authenticate: Bearer` ✅
  - `GET /api/legal-profile/me` with web_portal JWT → reaches auth dep
    (401 because user 1 not seeded; flow correct, real user would 200) ✅
- [x] `grep -rE "legalProfile|DocumentUpload|passport_|inn_|snils_"
      mini_app/src/ --include="*.tsx" --include="*.ts"` (excluding
      legal-acceptance.ts / useLegalAcceptance.ts) → **0 hits** ✅

## Open items (deliberately deferred)

1. **Playwright specs** for Phase 1 (`legal-profile-requires-web-portal.spec.ts`,
   `ticket-login.spec.ts` with safeRedirect coverage on bad redirects).
   Spec writing is non-trivial — needs the running compose-test stack +
   seeded users. Tracked as the next commit on this branch (or a
   follow-up branch) before the develop → main merge if you choose to
   block on UI E2E. Backend smokes above + 97 unit/integration tests
   already cover the auth contract end-to-end.

2. **BL-004** (tests/ baked into api docker image, deadline Phase 3) and
   **BL-005** (acts portal wiring, deadline Phase 2). See BACKLOG.md.

## Why these decisions exist (audit trail)

Two scope-policy decisions deserve explicit record:

1. **A.2 carve-out for accept-rules.** PHASE1_RESEARCH §1.A.2 originally
   classified the entire `contracts.py` surface as PII-adjacent. On
   review the user pointed out that `accept-rules` is not PII — request
   is two booleans, response is `{success}`. Routing it through
   web_portal-only would force every new mini_app user to bounce
   through the browser for what amounts to a flag-set. Resolution:
   carve out into `legal_acceptance.py` with `get_current_user` (both
   audiences); URL preserved. Scope rule: exception from heavy-strip is
   permitted only when the endpoint is provably non-PII, justification
   documented in router docstring + this CHANGES doc. If PII is ever
   required at the URL, the endpoint moves to web_portal-only
   immediately.

2. **OrdRegistration / OrdStatus retained.** Initial types prune
   included these because PHASE1_RESEARCH §1.A.2 listed them. On
   build-failure inspection, neither type contains PII (erid, status,
   provider, timestamps — placement registration metadata with the
   Russian advertising operator). Restored with a clarifying comment
   and removed from the forbidden-pattern guard.

## Process finding

This is the **third** case in Phase 0/1 where the plan didn't reflect
reality of code: PF.2 (401 vs 426 in Phase 0), O.1 (TS-import graph in
1.A research), and now O.5/V4-V5 (`accept-rules` PII-classification at
endpoint level). Not critical individually, but the pattern suggests
plan validation should include:
- (a) `tsc --noEmit` dry-run on `mini_app/`/`web_portal/` before plan
  freeze;
- (b) per-endpoint PII classification (request schema + response schema
  + service-side DB writes), not file-name heuristics;
- (c) audit of merged decisions from previous phases — Phase 1's plan
  still said "don't touch audit_middleware.py" and "401 for aud-less"
  even after Phase 0 follow-up (PF.2/PF.4) reversed both.

Tracked as **process-finding** for Phase 2 plan freeze: include items
(a)-(c) before the next phase starts.

🔍 Verified against: e415ebfdb6e8f2a8c9e0e5b76e83c4f0e8c9d0a2 | 📅 Updated: 2026-04-25T11:38:31Z
