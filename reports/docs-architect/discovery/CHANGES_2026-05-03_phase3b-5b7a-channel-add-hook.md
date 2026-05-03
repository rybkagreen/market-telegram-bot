# Phase 3b 5b.7a — Channel-add compliance hooks + G06 разморозка + user-role gate dispatcher

**Date**: 2026-05-03
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.7a.1 → 5b.7a.3 (2 code + 1 docs)
**Origin**: Phase 3b sub-block 5b.7a — closes BL-037 channel-add fail-fast precondition gap. SPLIT from larger 5b.7 plan: 5b.7a = C-A (channel-add hook); 5b.7b = C-B (PayoutComplianceService skeleton) + C-C (idempotency_key keying convention) — separate sub-block, separate session.

## Summary

- 5b.7a ships channel-add compliance hooks (API + bot) closing BL-037 fail-fast gap for owner channel addition pre-conditions.
- G06 (`OWNER_PAYOUT_METHOD_VALID`) `PHASE5_PENDING` marker (5b.4) разморожен — real-now body via existing `payout_repo.get_valid_for_owner` + `get_by_owner` lookup.
- User-role gate dispatcher pattern established (`check_gate_for_user` parallel to `check_gate`); G01-G06 user variants extracted via shared helpers (P4 once-correctly).
- Bot handler S-48 contract marker fix piggyback (O.4) — `add_channel_confirm` explicit `session.commit()` removed; `DBSessionMiddleware` autocommits.
- Baselines preserved: ruff `src/` 4, mypy `src/` 10, pytest unit +24 pass over 5b.6 baseline (covers both 5b.7a.1 and 5b.7a.2).

## Files modified

- `src/core/enums/gate_reason.py` — +1 entry (`PAYOUT_METHOD_INVALID`) for G06 real-now fail.
- `src/core/services/gates/owner_gates.py` — refactor: `_check_g0X_for_user_id` shared helpers + user-side variants (`check_g04_user`, `check_g05_user`, `check_g06_user`); G06 body replaced with real-now lookup.
- `src/core/services/gates/advertiser_gates.py` — symmetrical refactor: `_check_g0X_for_user_id` helpers + user-side variants (`check_g01_user`, `check_g02_user`, `check_g03_user`); placement-side signatures preserved.
- `src/core/services/legal_compliance_service.py` — `_USER_GATE_CHECKERS` registry + `check_gate_for_user` / `check_gates_for_user_role` dispatchers; `User` import.
- `src/api/routers/channels.py` — `create_channel` compliance hook (placed before Telegram round-trip); admin test-mode carve-out; `AuditLogRepo.log` entry on decline; `ChannelAddDeclinedError` raise with `extra.blockers[]`.
- `src/bot/handlers/owner/channel_owner.py` — `add_channel_confirm` compliance hook + decline UX (callback alert + remediation message + FSM clear); explicit `session.commit()` removed (S-48 O.4 fix).
- `tests/unit/test_owner_gates.py` — replaced 2 PHASE5_PENDING-marker tests with 4 real-now tests + 8 user-variant tests (net +10).
- `tests/unit/test_legal_compliance_service.py` — +4 dispatcher tests (G04 dispatch, NotImplementedError on unmapped gate, owner role 3-result, advertiser role 3-result).
- `tests/unit/api/test_channels_create.py` (NEW) — 6 tests (G04/G05/G06 fail paths, admin carve-out, non-admin test-mode, audit log).
- `tests/unit/test_bot_channel_owner.py` (NEW) — 4 tests (happy path, decline path, remediation message detail, audit log).
- `CHANGELOG.md` — Unreleased section appended.
- `reports/docs-architect/discovery/CHANGES_2026-05-03_phase3b-5b7a-channel-add-hook.md` (NEW — this file).

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.7a.1 | `ea789da` | feat(gates): G06 real body + user-role gate dispatcher + G01-G06 user variants |
| 5b.7a.2 | `d9fd7e7` | feat(channels): channel-add compliance hooks (API + bot) + bot S-48 marker |
| 5b.7a.3 | (this commit) | docs(phase3b): 5b.7a closure — channel-add compliance hooks + G06 разморозка |

## Phase A+B+C trace

Phase A+B artifact: `tmp/PHASE3B_5B7_INVESTIGATION_2026-05-03.md`. Findings driving Phase C decisions:

- **A.2 — Channel-add codepath audit.** Two surfaces: API `POST /api/channels/` (`src/api/routers/channels.py:312`) and bot `add_channel_confirm` callback (`src/bot/handlers/owner/channel_owner.py:351`). Both lacked legal-compliance pre-conditions. `ChannelAddDeclinedError` was defined (`src/core/exceptions.py:242-250`) but never raised.
- **A.3 — `_USER_ROLE_GATES` audit.** Resolution table existed (`legal_compliance_service.py:107-122`) but dispatcher `check_gates_for_user_role` was missing — only docstring promise. 5b.7a fills this.
- **A.11 — Cross-phase complications.** Existing `check_gate(gate, placement)` signature did not fit channel-add (no `PlacementRequest`). Resolved via parallel `check_gate_for_user(gate, user)` method + per-gate user-side variants (P4 once-correctly: refactor all 6 placement-side gates G01-G06 to share body via helpers).
- **A.13 — Scope split.** SPLIT into 5b.7a (C-A) + 5b.7b (C-B + C-C) — C-A urgency tier (production-readiness gap, BL-037 closure) different from C-B/C-C (Phase 5 architectural prep). STOP gate clarity per CLAUDE.md "Process discipline".
- **A.14 — DBSessionMiddleware behavior.** Bot middleware (`src/bot/middlewares/db_session.py:21-25`) calls `session.commit()` after handler success — autocommit. Explicit `session.commit()` at `add_channel_confirm:378` was redundant double-commit (no-op but blurred Pattern 1 contract for handlers). Removed in 5b.7a.2.

## Marina decisions (Q1-Q7 from Phase B.7)

| # | Question | Decision |
|---|---|---|
| Q1 | Scope split 5b.7 vs 5b.7a + 5b.7b | **(а)** SPLIT — 5b.7a = C-A (channel-add hook); 5b.7b = C-B (PayoutComplianceService skeleton) + C-C (idempotency_key keying) |
| Q2 | G06 carve-out vs real-now vs accept-block | **(а)** real-now G06 body (разморозка PHASE5_PENDING marker) — preserves plan §3.B.6 wording, no UX block, Phase 5 swap is clean |
| Q3 | Admin test-mode carve-out for channel-add | **(а)** carve-out — `is_admin and is_test=True` bypasses compliance check; mirrors §3.B.4 admin spirit |
| Q4 | Bot handler scope: include `add_channel_confirm`? | **(а)** INCLUDE — two-surface enforcement (single skip = leak); bot S-48 marker fix piggybacks per P4 |
| Q5 | idempotency_key shape | N/A для 5b.7a (5b.7b territory) |
| Q6 | PayoutComplianceService skeleton vs real | N/A для 5b.7a (5b.7b territory) |
| Q7 | `payout_service.create_payout` dead code cleanup in 5b.7? | **(b)** defer — flag в CHANGES + Phase 3 closure lessons. Pre-existing architectural debt; NDFL/NPD/velocity/cooldown logic dead today (router-side path duplicates simpler version without those guards). NOT 5b.7 charter. |

## Relationship to 5b.4 closure attribution

5b.4 closure CHANGES (`CHANGES_2026-05-02_phase3b-5b4-owner-gates.md`) attributed G06 body to "Phase 5 (real payout provider validation)". 5b.7a partially supersedes that attribution — real-now lookup body shipped now (channel-add hook §3.B.6 requires it).

Phase 5 still owns **provider-validated** payout method state:
- bank_card: YooKassa Payouts recipient-check verification
- sbp: SBP bank selector + recipient-check
- bank_transfer: BIK + correspondent-account validation (IE / LE)
- yoomoney: OAuth integration

5b.7a body checks "valid record exists in DB" (`payout_request.payout_method_type IS NOT NULL` + status NOT IN rejected/cancelled). Phase 5 will tighten "valid" to "provider-confirmed valid" — same gate, refined semantics across phases.

**Pattern parallel to 5b.6:** 5b.6 closure documented "markers complement bodies" for G17/G18. Same approach here: 5b.4 marker → 5b.7a real-now body → Phase 5 provider-validated body. Each iteration tighter, no contract change.

## Test coverage

### G06 placement-side (test_owner_gates.py)
4 cases: `no_payout_records_passes_pre_setup`, `valid_payout_method_passes`, `payout_records_but_none_valid_fails`, `skips_get_by_owner_when_valid_found` (perf optimization sanity).

### G04/G05/G06 user-side (test_owner_gates.py)
8 cases: `check_g04_user_complete_returns_pass`, `check_g04_user_missing_profile_fails`, `check_g04_user_passes_user_id_to_repo`, `check_g05_user_signed_returns_pass`, `check_g05_user_passes_owner_role`, `check_g06_user_no_payout_method_passes`, `check_g06_user_valid_method_passes`, `check_g06_user_invalid_method_fails`.

### Dispatcher (test_legal_compliance_service.py)
4 cases: `check_gate_for_user_owner_g04_dispatches`, `check_gate_for_user_unknown_gate_raises` (NotImplementedError for G07-G18), `check_gates_for_user_role_owner_returns_three_results`, `check_gates_for_user_role_advertiser_returns_three_results`.

### API hook (tests/unit/api/test_channels_create.py — NEW)
6 cases: `g04_fail_returns_403_with_remediation`, `g05_fail_returns_403_with_contracts_remediation`, `g06_fail_returns_403`, `admin_test_mode_bypasses_gates`, `non_admin_test_mode_does_not_bypass`, `logs_audit_on_decline`.

### Bot hook (tests/unit/test_bot_channel_owner.py — NEW)
4 cases: `happy_path_creates_channel`, `gates_fail_no_channel_created`, `remediation_message_includes_blocker_details`, `logs_audit_on_decline`.

## Verification

| Gate | Pre-5b.7a baseline | 5b.7a result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) — 5b.6 baseline | 62 fail / 592 pass / 654 collected | — |
| pytest unit — after 5b.7a.1 | — | 62 fail / 606 pass (+14) |
| pytest unit — after 5b.7a.2 | — | 62 fail / 616 pass (+10 over 5b.7a.1; +24 cumulative) |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` (untouched) |
| S-48 violations introduced | 0 | 0 (bot O.4 fix removed pre-existing redundant commit) |

## Deferred to production launch

These items consolidate into the Phase 3 closure batch → `BACKLOG.md` (single packaged commit). NOT inline `BACKLOG.md` commits per CLAUDE.md "Process discipline".

- **G06 provider-validated state** — Phase 5 swaps DB-only lookup with provider integration (bank account, SBP, YooMoney, YooKassa Payouts recipient-check). Current 5b.7a body checks "valid method record exists" via 5b.1.4 enum field; provider integration adds external validation.
- **mini_app declined-channel UX** — current 403 response per plan §3.D ("mini_app does not display gates") needs deeplink из mini_app в web_portal `/legal-profile` или `/contracts`. Frontend update needed.
- **web_portal channel-add error UI** — render `extra.blockers[]` array as actionable list (gate name + reason + remediation deeplink). Frontend update needed.
- **`/payout-methods` portal route** — G06 fail `remediation_url` currently `None` until /payout-methods page exists in portal.
- **Channel-add audit log retention** — `AuditLog` is append-only; production launch needs retention policy + query indices for compliance auditing.
- **Frontend `addChannel` mutation idempotency header (O.6)** — channel-add itself doesn't strictly need idempotency (UNIQUE on telegram_id+owner_id covers race), но если extend convention в будущем — frontend update.
- **`payout_service.create_payout` dead code (O.2 / Q7)** — full NDFL/NPD/velocity/cooldown logic dead today; production path duplicates simpler version без NDFL withholding (ФЗ-Налог compliance gap для individual owners). Cleanup Phase 5 / production-prep.
- **Bot path `is_test` admin carve-out (O.7)** — bot `add_channel_confirm` always uses `is_active=True`; API has `is_test = body.is_test and current_user.is_admin`. Inconsistency pre-existing, deferred.

## Lessons (for Phase 3 closure batch — NOT inline BACKLOG)

- **L23** — G06 `PHASE5_PENDING` marker в 5b.4 was conservative over-marking. Production wiring (channel-add hook §3.B.6) required real-now body. Pattern: marker rollback acceptable when downstream integration requires real semantics + real body trivially achievable via existing primitives. Surface marker decisions for "minimum required real semantics" review when wiring downstream consumers.
- **L24** — `LegalComplianceService.check_gate(gate, placement)` signature не fits non-transition contexts (channel-add has User, no PlacementRequest). Established sibling `check_gate_for_user(gate, user)` parallel pattern. Future non-transition gate invocations follow same pattern (advertiser-side preconditions etc.). User-side gate-checker variants extracted via shared `_check_gXX_for_user_id` helpers (P4 once-correctly) — both placement and user paths share body.
- **L25** — Plan §3.B.6 admin test-mode carve-out language missing; 5b.7a added per §3.B.4 admin spirit consistency (Marina Q3=(а)). Plan revision needed in Phase 3 closure to make carve-out explicit at the spec level for future readers.

## Out of scope (deferred to 5b.7b / future sub-blocks)

- **`PayoutComplianceService` skeleton** — 5b.7b territory.
- **`payout_request.idempotency_key` keying convention** — 5b.7b territory.
- **Frontend updates** — out of charter; UX updates flagged в "Deferred to production launch".
- **5b.7b sub-block contents** (skeleton + idempotency) — separate session, separate STOP gate.
- **`pending_gate_resolutions` JSONB persistence on placement** — Phase 3c transition-service integration territory.

## Notes

5b.7a reused 5b.4/5b.5/5b.6 precedents:
- `GateReason` enum extended (no architecture change)
- `_GATE_CHECKERS` registry unchanged (placement-side dispatch)
- `_USER_GATE_CHECKERS` parallel registry — sibling to placement-side
- Pure mocked unit test pattern (`MagicMock(spec=AsyncSession)` + `monkeypatch` on repo classes)
- Pattern 1 S-48 contract throughout dispatchers + checkers
- AuditLog write via `AuditLogRepo` (append-only, no sensitive PII)

🔍 Verified against: `d9fd7e7` | 📅 Updated: 2026-05-03T00:00:00Z
