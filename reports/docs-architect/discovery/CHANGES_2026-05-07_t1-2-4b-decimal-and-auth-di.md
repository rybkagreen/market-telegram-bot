# T1.2.4b — Pydantic Decimal 422 + auth DI refactor

**Branch:** feature/t1-2-test-failures-cleanup
**Sub-block:** T1.2.4b
**Date:** 2026-05-07
**Pre-state:** HEAD `70e47ab`, baseline 54F/986P/12S/0E
**Post-state:** HEAD `5de1ded`, baseline 53F/993P/11S/0E

## Goal

**B1** — fix Pydantic Decimal serialization in 422 validation responses
(production bug returning 500 instead of 422 на Decimal-bound numeric
constraint failures).

**B2** — refactor `_resolve_user_for_audience` и 3 user resolvers к accept
session via FastAPI DI вместо opening own via `async_session_factory()`.
Restore Q2=α fixture intent (single override).

## Implementation

### B1 — log_sanitizer fix

- Commit: `8a47400` (fix(api): use jsonable_encoder in sanitized validation handler)
- File: `src/api/middleware/log_sanitizer.py:60`
- Change: `jsonable_encoder()` wrap для `exc.errors()` в `JSONResponse` content
  (mirrors FastAPI's default `request_validation_exception_handler`).
- Tests:
  - Unskipped `tests/test_api_channel_settings.py::TestAPIChannelSettings::test_patch_invalid_price_422`
  - New regression test: `tests/unit/api/test_validation_error_handler.py`
    with 6 cases (5 parametrized via `Field(ge=Decimal("100"))` schema
    against in-process FastAPI app + 1 standalone direct invocation of the
    handler with Decimal in `input` and `ctx`).

### B2 — auth DI refactor

- Commit: `5de1ded` (refactor(api): inject db session into auth resolvers (Q2=α))
- Files (5):
  - `src/api/dependencies.py` — driver + 3 resolvers + `get_db_session` reorder
  - `tests/conftest.py` — fixture α 4-way → 1-way override (×2 fixtures)
  - `tests/unit/api/test_jwt_aud_claim.py` — direct-call sites + stub session methods
  - `tests/integration/test_ticket_bridge_e2e.py` — same stub session pattern
  - `tests/unit/api/test_pii_audience_pinning.py` — `_stub_db_session` registry-aware
- Source changes:
  - `_resolve_user_for_audience` accepts `session: AsyncSession` parameter
    (positional/required); `async with async_session_factory()` block removed
  - `get_current_user` / `get_current_user_from_mini_app` /
    `get_current_user_from_web_portal` add `Depends(get_db_session)` parameter
  - `get_db_session` reordered above the resolvers (was line 170, now line 31)
    because `Annotated[..., Depends(get_db_session)]` is evaluated at function
    definition time
- Caller side: 127 endpoints transparent (DI internal, no router edits)

## Verification

| Stage         | F  | P   | S  | E | Δ vs `70e47ab` |
| ------------- | -- | --- | -- | - | -------------- |
| Pre `70e47ab` | 54 | 986 | 12 | 0 | —              |
| Post Šаг 1    | 53 | 993 | 11 | 0 | -1F, +7P, -1S  |
| Post Šаг 2 (initial) | 64 | 982 | 11 | 0 | +10F (regressions during fix-forward) |
| Post Šаг 2 (fix-forward) | 53 | 993 | 11 | 0 | -1F, +7P, -1S (restored) |

Šаг 2 saw 11 test regressions surfaced after the source refactor — direct-call
sites in unit tests, stub session classes lacking `commit/rollback/close` no-ops,
and `_stub_db_session` not aware of the user registry. Marina chose fix-forward
(option (b)). Five files updated atomically с the source refactor; baseline
restored к the post-Šаг 1 envelope.

Admin watch-item (surprise #5 from probe report): `get_current_admin_user`
chains via `get_current_user_from_web_portal` which now accepts session via DI.
Unit/integration admin tests scoped к the refactor surface PASS (30/30, 1
pre-existing fsm_middlewares failure unrelated). E2E API admin tests deferred —
require running `nginx-test` Docker stack.

## Lessons

- **L54** — Pydantic 2 ValidationError `ctx['ge'/'le'/'gt'/'lt']`
  contains `Decimal` instance regardless of constraint literal type
  (`Field(ge=100)` vs `Field(ge=Decimal("100"))` produce identical ctx shape).
  Custom exception handlers consuming `e.errors()` MUST wrap content via
  `jsonable_encoder` (mirrors FastAPI default handler). Bare `json.dumps`
  fails on Decimal без default callable.

- **L55** — Phase A+B initial scope analysis can mis-classify
  when comparing surface-level field declarations к actual runtime serialization
  paths. Stage 5 empirical reproduction against actual handler caught
  misdiagnosis (early draft of `B1_scope.md` claimed bug doesn't fire on
  current endpoints; Stage 5 invocation of `ChannelSettingsUpdateRequest` +
  installed handler returned 500 on every numeric-out-of-range payload).
  L52 strengthening (probe ships raw data) prevented wrong Phase C.

- **L56** — Auth dep DI refactor unlocks fixture override
  simplification: 4-way → 1-way restores original Q2=α intent. Pattern: when
  test fixture override count > 1 для one DI chain, suspect bypassed DI
  somewhere в production code path.

- **L57** — Probe inventory for DI refactors must enumerate
  TWO classes that `Depends`-grep misses: (1) **direct calls** к the
  refactored function (8 sites in `test_jwt_aud_claim.py` plus 1 in
  `test_ticket_bridge_e2e.py`); (2) **stub session/factory classes** in test
  infrastructure (`stub_session_factory` monkey-patch + `_Session` lacking
  `commit/rollback/close` no-ops + `_stub_db_session` lacking awareness of
  user registries the auth path now reads from). Phase A+B probe для T1.2.4b
  enumerated only 127 `Depends`-style callers; missed both classes; surfaced
  as 11 regressions during Šаг 2 fix-forward. Future probes for similar
  refactors should grep direct calls (`grep -rn "await <fn_name>("`) and
  catalog stub session/factory classes (`grep -rn "monkeypatch.setattr.*async_session_factory\|class _Session"`).

(L54-L57 assigned per L43 no-amend rule — split commit follows.)

## Cumulative T1.2 progress

T1.2.4b closes 2 entries (B1 + B2). Cumulative T1.2: ~50/99 (~50%).

Remaining T1.2: T1.2.5 (deprecated tests batch + C20 main_menu + C15
decision) + T1.2.6 (ESCROW-001 architectural).

## Deferred to production launch

- **Adjacent admin fixture simplification** —
  `tests/unit/api/test_admin_payouts.py` has parallel 3-way override fixture
  (lines 112-122). Now simplifiable post-B2 refactor к 1-way. Out of T1.2.4b
  scope per Marina decision (Q2=a). Surface для T1.2.5 deprecated batch
  consideration.

- **`get_db_session` itself still uses `async_session_factory()`** — T1.2.4b
  B2 only refactored `_resolve_user_for_audience`. The session-yielding
  dependency `get_db_session` (lines ~31-44 post-reorder) remains a
  self-contained `async with async_session_factory()` block. Full elimination
  of `async_session_factory()` direct calls outside `src/db/session.py` is
  out of scope; future T1.2.4d B3 candidate (would reduce factory call sites
  from N to 0 outside `db/session.py`, completing Pattern 1 contract for the
  DI session-handling chain).

## Artifacts

- Phase A+B: `tmp/T1_2_4b_PROBE_REPORT.md` + supporting `tmp/T1_2_4b_*`
- Phase C ci-local: `tmp/T1_2_4b_step{1,2}_ci-local*.log`
- Phase C smoke: `tmp/T1_2_4b_step{1,2}_*_smoke.log`,
  `tmp/T1_2_4b_step2b{1,2,3}_*.log`

🔍 Verified against: `5de1ded` (Šаг 2 commit) | `8a47400` (Šаг 1 commit) | `70e47ab` (pre-Phase C HEAD) | 📅 2026-05-07
