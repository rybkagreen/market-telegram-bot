# Phase 3b 5b.5 — Publication + post-publication gate bodies G08-G12

**Date**: 2026-05-02
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.5.1 → 5b.5.3 (2 code + 1 docs)
**Origin**: Phase 3b sub-block 5b.5 — ships real bodies for compliance gates G08-G12 covering `escrow → published` and `published → completed` placement transitions.

## Scope

| Gate | Status | Approach |
|---|---|---|
| G08 | Real | Reads `OrdRegistration.erid` via `OrdRegistrationRepo.get_by_placement` |
| G09 | Real | Reads `OrdRegistration.contract_ord_id` (provider-side ID, NOT local `Contract` FK) |
| G10 | Real | Reads `placement.erid` (in-memory, no repo) — marker rendering precondition |
| G11 | Real | Reads `placement.message_id` (durable Telegram-acceptance signal) — Marina Q1=(b) |
| G12 | Real | Reads `OrdRegistration.status == "reported"` (set by `OrdService.report_publication`) |

All gate bodies are S-48 Pattern 1: receive `session: AsyncSession`, no `commit`/`flush`/`rollback`. Gate failure → `TransitionBlockedError` raised by transition service caller.

## Files modified

- `src/core/enums/gate_reason.py` — +5 entries (`ERID_NOT_REGISTERED`, `ORD_CONTRACT_NOT_REPORTED`, `PLACEMENT_TEXT_NOT_MARKED`, `PUBLICATION_NOT_VERIFIED`, `PUBLICATION_NOT_REPORTED_TO_ORD`)
- `src/core/services/gates/publication_gates.py` — replaced 3 `NotImplementedError` stubs (G08/G09/G10) with real bodies
- `src/core/services/gates/post_publication_gates.py` — replaced 2 `NotImplementedError` stubs (G11/G12) with real bodies
- `tests/unit/test_publication_gates.py` (NEW) — 11 cases (G08: 4, G09: 4, G10: 3)
- `tests/unit/test_post_publication_gates.py` (NEW) — 9 cases (G11: 4, G12: 5)
- `CHANGELOG.md` — Unreleased section appended
- `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3b-5b5-publication-gates.md` (NEW — this file)

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.5.1 | `57fa19d` | feat(gates): G08 + G09 + G10 publication-side bodies + tests |
| 5b.5.2 | `f15c207` | feat(gates): G11 + G12 post-publication bodies + tests |
| 5b.5.3 | (this commit) | docs(phase3b): 5b.5 closure — publication + post-publication gate bodies |

## Phase A+B+C trace

Phase A+B artifact: `tmp/PHASE3B_5B5_PUBLICATION_GATES_INVESTIGATION_2026-05-02.md` (61.7 KB). Findings driving Phase C decisions:

- **A.3 / A.4 — `OrdRegistration` model + write paths.** Single row creator: `OrdService.register_creative` (synchronous call from bot handler at escrow time, line `bot/handlers/placement/placement.py:464`). Status lifecycle: `pending` (default, never realized) → `token_received` → `erir_confirmed`/`erir_failed`/`erir_timeout` → `reported`. Repo `OrdRegistrationRepo.get_by_placement(placement_request_id)` is the canonical primitive — used by G08/G09/G12 directly.
- **A.5 — `PlacementRequest` ORD-related fields.** `placement.erid` mirrored from `OrdRegistration.erid` atomically by `OrdService`. `placement.message_id` set durably by `placement_repo.set_message_id` immediately after Telegram send (publication_service.py:305-308 — S-48 external-boundary commit). `placement.publication_verified` exists but has NO writer in current codebase — Block 1 hook awaiting Phase 6.
- **A.6 — ERID marker rendering.** Marker is computed JIT by `publication_service._build_marked_text` (NOT stored on `placement.ad_text`). G10 reads `placement.erid` precondition rather than the rendered marker — gate body does not invoke the helper.
- **A.7 — Publication verification authoritative signals.** `placement.message_id IS NOT NULL` is the durable Telegram-acceptance proxy — chosen for G11 (Q1=(b)).
- **A.8 — Phase 6 boundary (plan §6.B.3).** Phase 6 hardening removes `ord_block_publication_without_erid` flag and switches `_build_marked_text` to deterministic provider-based blocking. Gate G08 will share the same logic. 5b.5 implementation does NOT pre-empt — reads DB state only.
- **A.10 — Transition callers.** Both `escrow → published` and `published → completed` transitions originate from Celery tasks (publication_service via placement_tasks). Gate failure blocks automation; Phase 5 `pending_gate_resolutions` mitigates for is_test placements.
- **B.5 Marina decisions:** Q1=(b) message_id proxy for G11; Q2 keep distinct G08+G10; Q3 status-only for G12; Q4 inline test fixtures; Q5 no `PHASE6_PENDING` enum; Q6 `_GATE_CHECKERS` registry unchanged.

## Marina decisions (Q1-Q6)

| # | Question | Decision |
|---|---|---|
| Q1 | G11 boundary: `message_id` proxy vs Phase 6 marker | **(b)** — `placement.message_id IS NOT NULL` proxy |
| Q2 | G08+G10 distinct or fold? | **Keep distinct** (conceptually separate concerns: ORD-side vs placement-side) |
| Q3 | G12 status check semantics | **`status == "reported"` only** (no defensive `reported_at` clause) |
| Q4 | `_fake_ord_registration` location | **Inline per-test-file** (mirror of 5b.3/5b.4 precedent) |
| Q5 | Add `PHASE6_PENDING` enum? | **No** (G11 uses real-now signal; not needed) |
| Q6 | `_GATE_CHECKERS` registry update | **No change needed** (already wired to stubs) |

## Phase 6 boundary

Per plan §6.B.3, Phase 6 ("Contracts/Acts UX + ORD production hardening") will:
- Remove `ord_block_publication_without_erid` setting
- Switch `_build_marked_text` to deterministic `provider == "stub"` vs production blocking
- Align gate G08 with the same predicate
- (Likely) introduce a writer for `placement.publication_verified` (round-trip Telegram verification)

5b.5 gate bodies read DB state populated by current ORD orchestration only. No `provider == "stub"` logic encoded. No Block 1 hook columns read (`placement.publication_verified`, `OrdRegistration.published_at`, `OrdRegistration.deadline_at`) — they lack writers today.

## Test coverage

`tests/unit/test_publication_gates.py` — 11 cases:
- **G08 (4):** no_registration_row, row_exists_erid_none, erid_set_returns_pass, remediation_url_none_on_fail
- **G09 (4):** no_registration_row, row_exists_contract_ord_id_none, contract_ord_id_set_returns_pass, remediation_url_none_on_fail
- **G10 (3):** erid_none, erid_set, does_not_call_repos (no `session.execute/commit/flush/rollback`)

`tests/unit/test_post_publication_gates.py` — 9 cases:
- **G11 (4):** message_id_none, message_id_set, remediation_url_none_on_fail, does_not_call_repos
- **G12 (5):** no_registration_row, status_token_received, status_erir_confirmed, status_reported_returns_pass, remediation_url_none_on_fail

Reuses 5b.3/5b.4 mocked-pattern (MagicMock(spec=AsyncSession) + monkeypatch on repo classes). `_fake_ord_registration` and `_fake_placement` declared inline in each test file (Q4 decision).

## Verification

| Gate | Pre-5b.5 baseline | 5b.5 result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) | 62 fail / 558 pass / 620 collected | 62 fail / 578 pass / 640 collected (+20) |
| Snapshot tests (`test_contract_schemas.py`) | 23 pass | 23 pass |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| S-48: no new commit/flush/rollback in `gates/` | yes | yes (0) |
| Smoke import (`from src.core.services.gates import publication_gates, post_publication_gates`) | OK | OK |

## Out of scope (deferred)

- **Phase 6 ORD production hardening** (§6.B.3 — provider-based publication blocking, removal of `ord_block_publication_without_erid` flag, alignment with G08).
- **Phase 6+ writers for Block 1 hooks** (`placement.publication_verified`, `OrdRegistration.published_at`, `OrdRegistration.deadline_at`) — schedule TBD.
- **G07/G13-G18 gate bodies** — separate sub-blocks (G07 Phase 4 ДС; G13 5b.6 payout territory; G14-G18 Phase 4+).
- **Transition service integration** (`TransitionBlockedError` raise path, `pending_gate_resolutions` JSONB for is_test) — 5b.6+ territory.
- **L20 dead-code: skeleton `YandexOrdProvider` in `ord_yandex_provider.py`** — Phase 3 closure batch territory (real impl lives in `yandex_ord_provider.py`; skeleton is unreachable at runtime via `api/main.py` startup override).
- **`_global_provider` module-state in `ord_service.py:48`** — L8 architectural debt, closure batch.
- **`OrdRegistration.status` String(20) instead of Enum** — closure batch.

## Notes

5b.5 reused 5b.3/5b.4 precedents fully:
- `GateReason` enum extended (no architecture change)
- `_GATE_CHECKERS` registry unchanged (already wired to stubs at Foundation Block 2)
- Pure mocked unit test pattern (`MagicMock(spec=AsyncSession)` + `monkeypatch` on repo classes)
- Direct repo imports (`OrdRegistrationRepo`)
- Pattern 1 S-48 contract throughout
- `remediation_url=None` for all G08-G12 fails — these are automated background processes; user cannot directly self-resolve "ORD didn't get my erid registration". Frontend can render a "wait" / "contact support" message keyed off `reason_code`.

The G08 / G10 conceptual distinction (ORD-side registration vs placement-side rendering precondition) is preserved per Q2; both currently pass-or-fail together because `OrdService` writes both atomically. Phase 6 may introduce divergence (e.g., test-mode bypass of placement-side mark requirement) — keeping gates distinct preserves that option.

🔍 Verified against: `f15c207` | 📅 Updated: 2026-05-02T00:00:00Z
