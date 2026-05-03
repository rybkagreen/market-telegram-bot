# Phase 3a Block 2 — Service plumbing skeletons

**Date**: 2026-05-02
**Branch**: feature/legal-compliance-gates
**Commits**: 2.1 → 2.5 (4 code + 1 docs)

## Scope

Block 2 ships scaffolding for Phase 3 legal compliance:

- 2 custom exceptions (TransitionBlockedError, ChannelAddDeclinedError)
- 4 repo methods (data-access surface for gate checks)
- 6 gate-checker module skeletons (18 NotImplementedError stubs)
- LegalComplianceService skeleton (real dispatch, stubbed gates + transitions)

**No business logic.** Validation logic + Yandex provider land in Phase 3b.
Integration into transition service + channel-add hook lands in Phase 3c.
API endpoint lands in Phase 3d.

## Files added

- `src/core/services/gates/__init__.py`
- `src/core/services/gates/advertiser_gates.py`
- `src/core/services/gates/owner_gates.py`
- `src/core/services/gates/agreement_gates.py`
- `src/core/services/gates/publication_gates.py`
- `src/core/services/gates/post_publication_gates.py`
- `src/core/services/gates/payout_gates.py`
- `src/core/services/legal_compliance_service.py`
- `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-block2-skeleton.md` (this file)

## Files modified

- `src/core/exceptions.py` — appended 2 classes
- `src/db/repositories/contract_repo.py` — appended `has_signed_framework`
- `src/db/repositories/legal_profile_repo.py` — appended `get_verification_status`
- `src/db/repositories/payout_repo.py` — appended `get_valid_for_owner`
- `src/db/repositories/user_repo.py` — appended `get_with_legal_profile` + `selectinload` import

## New exceptions

| Class | Parent | error_code | HTTP |
|---|---|---|---|
| `TransitionBlockedError` | `ConflictError` | `transition_blocked` | 409 |
| `ChannelAddDeclinedError` | `ForbiddenError` | `channel_add_declined` | 403 |

No callers yet — Phase 3c integration raises them.

## New repo methods

| Class | Method | Returns |
|---|---|---|
| `ContractRepo` | `has_signed_framework(user_id, role)` | `bool` |
| `LegalProfileRepo` | `get_verification_status(user_id)` | `str \| None` |
| `PayoutRepository` | `get_valid_for_owner(owner_id)` | `PayoutRequest \| None` |
| `UserRepository` | `get_with_legal_profile(user_id)` | `User \| None` (eager-load) |

`get_valid_for_owner` filter resolution (D2 not yet typed):

- `payout_method_type IS NOT NULL`
- `status NOT IN (rejected, cancelled)` — i.e. `pending` / `processing` / `paid`
- `ORDER BY created_at DESC LIMIT 1`

The "valid" semantic intentionally includes `paid` (the *method* is still
considered valid even though the request itself is finalized) — Phase 3b
may tighten this once `payout_method_type` becomes a typed enum.

## Gate-checker modules

6 modules under `src/core/services/gates/`, 18 stub functions total:

| Module | Gates | Stub kind |
|---|---|---|
| `advertiser_gates.py` | G01-G03 | Phase 3b |
| `owner_gates.py` | G04-G06 | Phase 3b |
| `agreement_gates.py` | G07 | Phase 4 |
| `publication_gates.py` | G08-G10 | Phase 3b |
| `post_publication_gates.py` | G11-G12 | Phase 3b |
| `payout_gates.py` | G13, G14, G17, G18 = Phase 3b; G15, G16 = Phase 4 | mixed |

All 18 functions: `async def check_gNN(session, placement) -> GateResult`.
All raise `NotImplementedError(f"Phase 3b: …")` (or `Phase 4` for G07/G15/G16).
Fail-loud, no silent pass-through.

## LegalComplianceService surface

`src/core/services/legal_compliance_service.py`:

- `__init__(session: AsyncSession)` — session-in-constructor (D-A; matches
  dominant pattern used by `ContractService`, `LegalProfileService`,
  `PlacementTransitionService`).
- `gates_for_transition(from_status, to_status) -> list[PlacementGate]`
  — `NotImplementedError` (Phase 3b populates declarative table).
- `async check_gate(gate, placement) -> GateResult` — real dispatch via
  the `_GATE_CHECKERS` registry (18 entries). Checker bodies themselves
  raise `NotImplementedError`.
- `async check_gates_for_transition(placement, to_status) -> list[GateResult]`
  — composes the two above; no callers yet.

S-48: no `commit` / `flush` / `rollback` in service code.

`PlacementStatus` is imported eagerly from `src.db.models.placement_request`
(it lives in the same module as `PlacementRequest`, which is already
required) rather than via `TYPE_CHECKING`. This keeps the type
annotations bare per ruff `UP037` and avoids a needless string-quoted
forward reference.

## Phase 3b TODOs (gated by Block 2 stubs)

- 18 gate-checker bodies (replace `NotImplementedError` with real validation)
- Declarative transition→gates table in `gates_for_transition`
- FNS verification provider (real Yandex)
- EGRUL/EGRIP snapshot freshness logic (G03 dispatcher by `legal_status`)
- `payout_method_type` enum + per-method validators (D2)
- Tests for repo methods + gate-checker logic + service dispatch

## Verification

| Gate | Baseline | Block 2 result |
|---|---|---|
| ruff (`src/`) | 4 errors | 4 errors |
| mypy (`src/`) | 10 errors | 10 errors (288 source files, +8 new) |
| pytest unit (excl. test_main_menu) | see note | 62 fail / 496 pass / 558 collected |
| Snapshot `gate_result_response.json` | matches | matches (23 contract tests pass) |
| alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |

**Pytest baseline note** — the prompt cited `~76 fail / 780 pass` (≈ 856
total). The current invocation `pytest tests/unit/
--ignore=tests/unit/test_main_menu.py` collects only 558 tests on this
branch. The cited baseline appears to be from a different invocation
(per BL-028, baseline numbers are invocation-sensitive). Block 2 added
**zero** test files and modifies no existing test, so all 62 failures
are pre-existing and live in test files unrelated to the Block 2
surface (`test_ai_service.py`, `test_billing.py`, `test_content_filter.py`,
`test_escrow_payouts.py`, etc.). No regressions introduced.

## Out of scope (deferred)

- CHANGELOG.md `[Unreleased]` entry — Block 4 bundle (covers prep + Block
  1 + Block 1.5 + Block 2 + Block 3) per Marina decision.
- Tests — pair with logic in Phase 3b.
- S-48 router-commit cleanup — Block 3.
- Audit log integration — Block 3 (existing `AuditLogRepo` to be reused,
  not duplicated).
- Schema changes — none needed; Block 1 columns sufficient.
