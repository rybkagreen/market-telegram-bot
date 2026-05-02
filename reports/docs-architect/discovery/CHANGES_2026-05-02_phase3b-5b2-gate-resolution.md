# Phase 3b 5b.2 — Gate resolution methods

**Date**: 2026-05-02
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.2.1 → 5b.2.3 (2 code + 1 docs)
**Origin**: Phase 3b sub-block sequencing; LegalComplianceService skeleton (Foundation Block 2) needed real resolution-layer methods before gate bodies (5b.3+).

## Scope

Two new pure-resolution methods on `LegalComplianceService`:

| Method | Purpose | Returns |
|---|---|---|
| `gates_for_transition(from, to)` | Which gates apply to a placement state transition | `list[PlacementGate]` |
| `gates_for_user_role(role)` | Which gates apply to a user acting in a given role (non-transition) | `list[PlacementGate]` |

Both are pure (don't touch `self._session`); used as resolution layer feeding `check_gate` dispatch (already real from Foundation Block 2) or future async check companions.

## Files modified

- `src/core/services/legal_compliance_service.py` — added `_TRANSITION_GATES` and `_USER_ROLE_GATES` module constants, replaced `gates_for_transition` body, added `gates_for_user_role` method, added `Literal` import
- `tests/unit/test_legal_compliance_service.py` (NEW) — 27 test cases

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.2.1 | `53263cf` | feat(legal): gates_for_transition resolution table |
| 5b.2.2 | `a4b3eba` | feat(legal): gates_for_user_role resolution method |
| 5b.2.3 | (this commit) | docs(phase3b): 5b.2 closure — gate resolution methods |

## Phase A+B → Phase C trace

Phase A (investigation) + Phase B (design proposal) lived in `tmp/PHASE3B_5B2_TRANSITION_TABLE_INVESTIGATION_2026-05-02.md`. Five plan-vs-code conflicts and design questions surfaced; Marina sign-off resolved each:

| Q | Decision | Effect |
|---|---|---|
| Q1 | Exclude G13-G18 from transition table | Payout-side gates belong to PayoutRequest lifecycle (Phase 5); plan §3.B.1 "completed → payout_processing" was a layer-mismatch in plan |
| Q2 | Include `"advertiser"` role | Symmetric design; G01-G03 fit same pattern as G04-G06 |
| Q3 | Plain `ValueError` for unknown transition | Avoids cross-service coupling (no import from `placement_transition_service`); `InvalidTransitionError` extends `ValueError` so callers handling either work uniformly |
| Q4 | Drop `user` param from `gates_for_user_role` | Resolution layer is pure role lookup; agent caught planner-side prompt drift and surfaced as Marina decision rather than silently dropping (positive P3+P5 precedent — recorded as L17 candidate for Phase 3 closure) |
| Q5 | Raise `ValueError` for unknown role | `Literal` blocks at type-check; runtime is defence-in-depth |

## Resolution table contents

`_TRANSITION_GATES`: 19 entries mirroring `placement_transition_service._ALLOW_LIST` exactly.

| Transition | Gates |
|---|---|
| `pending_owner → pending_payment` | {G07} |
| `counter_offer → pending_payment` | {G07} |
| `escrow → published` | {G08, G09, G10} |
| `published → completed` | {G11, G12} |
| 15 other transitions | ∅ (no compliance preconditions) |

`_USER_ROLE_GATES`:
- `"owner"` → {G04, G05, G06}
- `"advertiser"` → {G01, G02, G03}

## Test coverage

`tests/unit/test_legal_compliance_service.py` — 27 cases:

- 19 parametrized — table lookup verifies all transitions return expected gate sets
- 3 unknown-pair — verify `ValueError` raised
- 1 consistency invariant — `_TRANSITION_GATES` keys exactly match `_ALLOW_LIST` flattened (catches future drift between gates table and placement allow-list)
- 1 owner role
- 1 advertiser role
- 2 unknown-role parametrized

Pure-logic tests using `MagicMock(spec=AsyncSession)` — no DB, no async fixtures, no testcontainer.

## Verification

| Gate | Pre-5b.2 baseline | 5b.2 result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. `test_main_menu`) | 62 fail / 496 pass / 558 collected | 62 fail / 523 pass / 585 collected (+27 pass / +27 collected) |
| Snapshot tests (`test_contract_schemas.py`) | 23 pass | 23 pass |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` |
| S-48: no new commit/flush/rollback in service | yes | yes |

## Out of scope (deferred)

- Gate bodies — remain `NotImplementedError`; Phase 3b 5b.3+ ships logic
- `check_gates_for_user_role` async companion — downstream of resolution; sub-block 5b.5 territory (channel-add hook will call it)
- Integration into `PlacementTransitionService.transition()` — sub-block 5b.9
- Phase 5 stub markers — G06/G18 marker change deferred to 5b.10 closure
- All architectural debt surfaces (placementstatus enum 4-counts, fns_verification_status varchar vs Enum, mini_app stale comment per L14, migrations count drift) — Phase 3 closure batch
- L16/L17 codification — Phase 3 closure batch

## Lessons accumulating for Phase 3 closure batch

- **L17 (new)** — Agent self-audit catches planner-side prompt drift. Q4 was a casual signature in planner prompt (`user: User, role: ...`); agent caught unused param via P3 self-check and surfaced as Marina decision rather than silently following or silently dropping. Reinforces that Engineering Principles protect against planner errors as well as plan errors.

## Notes

5b.2 is the resolution-layer foundation for 5b.3-5b.7 (gate bodies), 5b.5 (channel-add hook), and 5b.9 (transition service integration). All downstream work calls these two methods.
