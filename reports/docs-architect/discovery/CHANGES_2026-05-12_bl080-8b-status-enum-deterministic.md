# CHANGES — BL-080 8b: Status enum + Phase 6.B.3 deterministic logic

**Date:** 2026-05-12
**Branch:** `feature/bl080-8b-status-enum-deterministic`
**Base:** develop @ `7f4e47f` (post-8a merge)

## Closes

- **BL-080 T3.19 absorbed** — `OrdRegistration.status` `String(20)` → `Enum` migration
- **Phase 6.B.3 core deterministic logic** — existing plan slot fully delivered
  (`ord_provider` literal, removal of `ord_block_publication_without_erid`,
  `_build_marked_text` rewrite, Gate G08 alignment)

## Resolves (from BL-080 probe surprises)

- **S5** — `ord_blocked` referenced but absent. Now defined как
  `OrdRegistrationStatus.ord_blocked` (Q4=(a) decision).
- **S9** — `ord_block_publication_without_erid` setting was supposed to be removed
  by Phase 6.B.3 plan; this sub-block removes it together с the callers.

## Decisions applied

- **Q4 = (a)** — `ord_blocked` is a distinct status, not aliased к `erir_failed`.
  Captures ORD-side rejection of the creative, separable from generic ERIR
  failure modes.
- **Q8 = (a)** — `0001_initial_schema.py` edited in place per pre-prod migration
  policy (Marina-approved exception к migration immutability rule); no new
  Alembic revision file.

## Summary

The OrdRegistrationStatus enum (7 values — 6 stored states observed in code plus
ord_blocked) replaces the loose `String(20)` column. The migration edits the
inline `sa.Enum` declaration in `0001_initial_schema.py`, mirroring the existing
`placementstatus` / `payoutstatus` patterns. The SQLAlchemy model column,
`OrdRegistrationRepo.update_status` signature, and all internal callsites in
`src/core/services/ord_service.py` and `src/tasks/ord_tasks.py` use enum members
where they previously used string literals; str-Enum semantics keep external
string-comparing tests stable.

`_build_marked_text` was rewritten per Phase 6.B.3 plan code: under
`ord_provider="stub"` (and only под stub) publication proceeds без an ERID
marker, with a `[ТЕСТОВАЯ ПУБЛИКАЦИЯ]` footer if `placement.is_test` is set.
Any other provider value raises the new `PublicationBlockedError`
(`src/core/exceptions.py`) when ERID is missing. When ERID is present the
existing "Реклама. <name>\nerid: <token>" disclaimer composition is preserved.
Gate G08 (`src/core/services/gates/publication_gates.py`) follows the same
deterministic conditional and short-circuits to pass under stub. The
`ord_block_publication_without_erid` setting is gone (Pydantic field removed,
all references rewritten).

Acceptance tests cover the four conditional branches (yandex+no-erid → blocked,
stub+is_test → TEST label, stub+normal → clean text, erid present → disclaimer)
plus G08 stub short-circuit.

## Files touched

- `src/db/models/ord_registration.py` — added `OrdRegistrationStatus(str, Enum)`
  (7 members); status column converted to `Mapped[OrdRegistrationStatus]`
- `src/db/migrations/versions/0001_initial_schema.py` — inline `sa.Enum` for
  `ord_registrations.status` (replaces `String(20)`); name=`ordregistrationstatus`
- `src/db/repositories/ord_registration_repo.py` — `update_status` signature
  `str → OrdRegistrationStatus`
- `src/core/services/ord_service.py` — INSERT и `report_publication` use enum
  members for status; import added
- `src/tasks/ord_tasks.py` — 4 `update_status` callsites + terminal-state set
  use enum members; import added; `.value` used where string is consumed by
  external string-comparing callers (logger.info return strings preserved)
- `src/config/settings.py` — `ord_provider` typed as
  `Literal["stub","yandex","vk","ozon"]`; `ord_block_publication_without_erid`
  removed; `Literal` import added
- `src/core/exceptions.py` — new `PublicationBlockedError(RuntimeError)`
- `src/core/services/publication_service.py` — `_build_marked_text` rewritten
  per Phase 6.B.3 plan (stub vs non-stub deterministic branching);
  `PublicationBlockedError` import added
- `src/core/services/gates/publication_gates.py` — G08 short-circuits to pass
  on `settings.ord_provider == "stub"` per Phase 6.B.3 alignment; `settings`
  import added
- `tests/unit/test_publication_gates.py` — 3 G08 blocker tests monkeypatch
  `ord_provider="yandex"` to exercise the non-stub path; 1 new test for
  stub short-circuit pass
- `tests/integration/test_placement_transition_service.py` —
  `test_multi_blocker_collect_all` monkeypatches `ord_provider="yandex"` so
  G08 remains in the failing set
- `tests/test_publication_service.py` — `TestBuildMarkedTextDeterministic`
  class with 4 acceptance tests

## Sub-block status (BL-080 § 8 plan)

- **8a closed** ✓ (provider unification + DI, merged develop)
- **8b closed** ✓ — status enum + deterministic logic
- **8c pending** — ERID flow hardening (idempotency race-window fix, retry
  refinement, audit trail / correlation_id, failure paths enumeration,
  admin override endpoint)
- **8d pending** — caption budget impl (legal-gated)

## Baselines

| Gate | Pre-8b (develop `7f4e47f`) | Post-8b (Шаг 7) |
|---|---|---|
| `make format-check` | 0 errors / 400 files | 0 errors / 400 files |
| `make lint` | 7 errors (BL-024 baseline) | 7 errors (BL-024 baseline) |
| `make typecheck` | 0 errors / 292 files | 0 errors / 292 files |
| `make ci-local` pytest | 1013P / 2S / 0F / 0E | **1018P** / 2S / 0F / 0E (+5) |
| `ci-local` exit | 1 (lint baseline) | 1 (lint baseline) |

Pytest gain: 1 test added in Шаг 4 (G08 stub short-circuit) + 4 acceptance tests
in Шаг 5. File counts unchanged (no new src files; both new tests are inside
existing files).

Шаг 6 stability check: two consecutive ci-local runs each yielded `1018 passed,
2 skipped` with identical durations (~180s). No flakiness.

## Not included (8c / 8d scope)

- Idempotency race-window fix (INSERT-before-call pattern, S-48 mirror)
- Retry policy refinement (linear → exponential + jitter, Q3 pending)
- Audit trail capture (request/response payloads, correlation_id linkage to
  `placement_status_history`)
- Failure paths enumeration with per-category recovery paths
- Admin override endpoint для `ord_blocked` / `erir_failed` recovery
- Caption budget Option A / B / C / hybrid impl (Q1, legal-gated)
- BACKLOG.md updates (batched к Phase 3 closure)

## Verification

- **S5 — `ord_blocked` defined**: `OrdRegistrationStatus.ord_blocked` accessible
  from any module via `from src.db.models.ord_registration import
  OrdRegistrationStatus`. Migration enum list includes the value, so column
  accepts it at the DB level.
- **S9 — `ord_block_publication_without_erid` purged**: `rg 'ord_block_publication_without_erid'
  src/ tests/` returns empty. Pydantic Settings класс no longer defines the field;
  pytest collection on fresh state passes.
- **Phase 6.C acceptance tests** (`tests/test_publication_service.py::TestBuildMarkedTextDeterministic`):
  - `test_publication_blocked_when_no_erid_non_stub_provider` — yandex provider + no erid → `PublicationBlockedError`
  - `test_publication_test_label_when_stub_provider_is_test` — stub + is_test → `[ТЕСТОВАЯ ПУБЛИКАЦИЯ]`
  - `test_publication_normal_text_when_stub_provider_not_test` — stub + not is_test → clean text
  - `test_publication_disclaimer_appended_when_erid_present` — erid set → disclaimer appended

🔍 Verified against: `feature/bl080-8b-status-enum-deterministic` HEAD post-Шаг 6
📅 Updated: 2026-05-12
