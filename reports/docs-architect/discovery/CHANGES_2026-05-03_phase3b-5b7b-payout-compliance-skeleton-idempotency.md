# Phase 3b 5b.7b — PayoutComplianceService skeleton + X-Idempotency-Key keying + P4 cleanups

**Date**: 2026-05-03
**Branch**: feature/phase3b-compliance-gates
**Commits**: 5b.7b.1 → 5b.7b.3 (2 code + 1 docs)
**Origin**: Phase 3b sub-block 5b.7b — closes 5b.1.3 deferral comment in `payout_request.idempotency_key` (`src/db/models/payout.py`), establishes Phase 5 architectural boundary for payout-side gate dispatch, applies three P4 once-correctly cleanups bundled while the relevant files are being touched.

## Summary

- 5b.7b ships `PayoutComplianceService` skeleton (Option A — empty registries + populated dispatchers) as the Phase 5 boundary for payout-side gate evaluation. Mirrors `LegalComplianceService` precedent established in 5b.7a.
- `POST /api/payouts/` gains `X-Idempotency-Key` header support with server-side UUID4 fallback. EXISTS-check fast path + race-past-EXISTS handling via strict-distinguish IntegrityError introspection. Mirrors admin topup precedent at `routers/admin.py:744`.
- Three P4 once-correctly cleanups bundled (CL-1/CL-2/CL-3) per Marina cleanup directive — same module family being touched, verification cheap.
- Baselines preserved: ruff `src/` 4, mypy `src/` 10, pytest unit +17 pass over 5b.7a baseline (cumulative across both code commits).

## Files modified

- `src/core/services/payout_compliance_service.py` (NEW, ~115 LOC) — Pattern 1 S-48 service with three empty registries and five dispatcher methods. Four methods fully wired (`gates_for_payout_transition`, `gates_for_payout_create`, `check_gate`, `check_gates_for_payout_transition`); `check_gates_for_payout_create` raises `NotImplementedError` by design (signature impedance per O.I — Phase 5 chooses dispatch path). Service partition (Q6=(а)): payout-specific gates only (G13-G18); user-role gates remain `LegalComplianceService` territory.
- `src/utils/db_errors.py` (NEW, ~30 LOC) — `extract_constraint_name(error: IntegrityError) -> str | None` helper. Encapsulates asyncpg-vs-aiosqlite IntegrityError diag divergence; returns None when constraint name not extractable; caller convention treats None as no-match (re-raise per strict-distinguish semantics).
- `src/db/models/payout.py` — `IDEMPOTENCY_KEY_CONSTRAINT_NAME` module-level constant added next to column declaration; mirrors migration `0001_initial_schema.py:816` literal. Production code (router error handler) AND tests import this constant — single source of truth.
- `src/api/routers/payouts.py` — `create_payout` gains `x_idempotency_key: Annotated[str | None, Header(alias="X-Idempotency-Key")] = None` parameter. EXISTS-check fast path before construction; idempotency key shape `payout_request:owner={user_id}:nonce={header|uuid4_hex}`. Strict-distinguish IntegrityError handler returns existing on `ix_payout_requests_idempotency_key` collision and re-raises other constraint violations. CL-1: explicit `await session.commit()` removed; uses `session.flush()` instead — `get_db_session` autocommits on handler success.
- `tests/unit/test_payout_compliance_service.py` (NEW, ~140 LOC) — 7 tests: smoke + 4 empty-registry semantics + ValueError propagation + monkeypatch dispatch verification (proves dispatcher logic is real, Phase 5 only populates registries).
- `tests/unit/utils/test_db_errors.py` (NEW, ~50 LOC) — 4 tests for `extract_constraint_name`: asyncpg shape, no orig, no diag attribute (aiosqlite shape), empty constraint name.
- `tests/unit/test_payouts_idempotency.py` (NEW, ~245 LOC) — 6 tests: EXISTS-fast-path replay, UUID4 fallback distinct keys, race-past-EXISTS handled idempotently, other-IntegrityError re-raise, key shape regex, header value plumbing.
- `CHANGELOG.md` — Unreleased section appended.
- `reports/docs-architect/discovery/CHANGES_2026-05-03_phase3b-5b7b-payout-compliance-skeleton-idempotency.md` (NEW — this file).

## Commits

| # | Hash | Title |
|---|---|---|
| 5b.7b.1 | `a66a462` | feat(payouts): PayoutComplianceService skeleton (Phase 5 boundary) |
| 5b.7b.2 | `cbe59bd` | feat(payouts): X-Idempotency-Key keying + CL-1/CL-2/CL-3 cleanups |
| 5b.7b.3 | (this commit) | docs(phase3b): 5b.7b closure — skeleton + idempotency + P4 cleanups |

## Phase A+B+C trace

Phase A+B artifact: `tmp/PHASE3B_5B7B_INVESTIGATION_2026-05-03.md` (post-5b.7a delta verification + final design). Findings driving Phase C decisions:

- **A.1 — 5b.7 conclusions still hold post-5b.7a.** A.4/A.5/A.7 unchanged (`PayoutComplianceService` doesn't exist, 4 PayoutRequest creation sites with #2-4 dead, no Celery retry). A.11 RESOLVED by 5b.7a (`check_gate_for_user` parallel pattern landed) — strengthens C-B precedent.
- **A.2 — Skeleton design refinement.** Option A (empty registries + populated dispatchers) vs Option B (all NotImplementedError stubs). Option A wins: mirrors 5b.7a `_USER_GATE_CHECKERS` precedent; Phase 5 cost reduction (just populate registries; no method-body rewrites for the wired dispatchers).
- **A.2.4 — `gates_for_payout_create` + `check_gates_for_payout_create` added.** Phase 5 will need both `*_transition` and `*_create` resolution paths. Skipping `*_create` in skeleton forces Phase 5 to add it later — bigger Phase 5 commit + signature design at integration time. Method bodies: `gates_for_payout_create` populated dispatcher with empty `_PAYOUT_CREATE_GATES` table; `check_gates_for_payout_create` raises `NotImplementedError` (O.I signature impedance).
- **A.3 — Idempotency keying convention.** Header name = `X-Idempotency-Key` (mirror admin topup); fallback = random UUID4; key shape = `payout_request:owner={user_id}:nonce={header|uuid}`; race-past-EXISTS handled via IntegrityError + re-read.
- **A.5.3 — Service partition.** Three options: (a) duplicate registries, (b) composition, (c) clean partition. Recommendation (c): `PayoutComplianceService` owns ONLY payout-specific gates; caller invokes BOTH services for full payout-create gate evaluation. No circular delegation; clean boundaries.

## Marina decisions (Q1-Q6 + cleanup directive)

| # | Question | Decision |
|---|---|---|
| Q1 | Skeleton style: Option A (empty registries + populated dispatchers) vs Option B (all NotImplementedError) | **(а)** Option A — mirrors 5b.7a precedent; dispatcher logic ships permanent; Phase 5 changes are additive registry inserts only |
| Q2 | Add `gates_for_payout_create` + `check_gates_for_payout_create` to skeleton? | **(а)** YES — Phase 5 wiring economy; signature lock-in committed now |
| Q3 | Header parameter name: `X-Idempotency-Key` vs `Idempotency-Key` (RFC) | **(а)** `X-Idempotency-Key` — internal consistency with admin topup |
| Q4 | Server fallback when header absent: random UUID vs deterministic vs hybrid | **(а)** header → random UUID4 fallback (admin pattern; deterministic breaks legitimate sequential payouts) |
| Q5 | Distinguish IntegrityError on idempotency_key UNIQUE vs other? | **(б) STRICT distinguish** — race-past-EXISTS only on `ix_payout_requests_idempotency_key`; other constraint violations re-raise honestly |
| Q6 | `check_gates_for_payout_create` partition: caller invokes both services? | **(а)** Clean partition (PayoutCompliance owns G13-G18 only; LegalCompliance owns G04-G06) — no circular delegation |

**Cleanup directive (P4 once-correctly, Marina 2026-05-03):**

- **CL-1** — Removed pre-existing redundant `await session.commit()` at `routers/payouts.py:194` (O.D). Pre-flight verified `get_db_session` autocommits on success (`src/api/dependencies.py:170-183` — `yield session` then `await session.commit()`). Mirrors 5b.7a O.4 fix in bot handler. Router uses `session.flush()` to surface IntegrityError synchronously.
- **CL-2** — Module-level constant `IDEMPOTENCY_KEY_CONSTRAINT_NAME = "ix_payout_requests_idempotency_key"` in `src/db/models/payout.py` next to column declaration. Production code (router) AND tests import it — no duplicated literals.
- **CL-3** — Helper `extract_constraint_name(error: IntegrityError) -> str | None` in NEW module `src/utils/db_errors.py`. Encapsulates asyncpg-vs-aiosqlite `e.orig.diag` divergence; returns None when constraint name not extractable; conservative no-match treatment by caller.

CL-1/CL-2/CL-3 within sub-block scope per P1: same module family being edited (router + model + utils helper supporting payouts).

## Relationship to 5b.1.3 / 5b.7a closure attribution

**5b.1.3 deferral closure.** `payout_request.idempotency_key` field was added in 5b.1.3 with the model-side comment "service-level keying convention deferred to 5b.7 (payout-side gates)". 5b.7b closes that deferral by adding the keying convention at the only active creation site (`routers/payouts.py:create_payout`). Comment updated to point at 5b.7b. The other three PayoutRequest creation sites (`payout_service.create_payout`, `request_payout_for_placement`, `create_pending_payout`) remain dead code per 5b.7 A.5 / Marina Q7=(b) deferral — when (if) Phase 5 revives them, they'll inherit the same keying convention.

**5b.7a O.4 mirror.** 5b.7a fixed S-48 contract marker in bot `add_channel_confirm` handler (explicit `session.commit()` removed; `DBSessionMiddleware` autocommits). 5b.7b CL-1 applies the same fix to router `create_payout` (explicit `session.commit()` removed; `get_db_session` autocommits). Same root pattern (handler-level autocommit by dependency/middleware), two surfaces. Now consistent across bot and API.

## Skeleton design rationale

**Option A (empty registries + populated dispatchers) chosen over Option B (all NotImplementedError).**

| Criterion | Option A | Option B |
|---|---|---|
| Mirrors 5b.7a `_USER_GATE_CHECKERS` precedent | YES | NO |
| Phase 5 friction | LOW (populate registries) | MEDIUM (rewrite method bodies) |
| Test surface today | Real dispatch verification possible (test 7 monkeypatches registry) | Smoke tests only (each method raises) |
| Architectural commitment | Structure committed (registry shape + dispatcher invariants) | Only API committed (signatures) |
| LOC | ~115 | ~30 |
| P4 once-correctly | Better (Phase 5 changes are additive) | Worse (Phase 5 rewrites bodies) |

**`check_gates_for_payout_create` NotImplementedError by design (O.I).** Signature impedance: `check_gate` takes `PayoutRequest`, but at create-time there is no `PayoutRequest` (only `User`). Two Phase 5 resolutions: (a) introduce dual-signature checker registry (`PayoutGateCheckerFn` for placement-keyed + `Callable[[AsyncSession, User], ...]` for user-keyed) OR (b) construct a draft `PayoutRequest` for dispatch. Skeleton commits to method signature only — Phase 5 chooses path. Documented inline in service docstring.

**Q6 partition rationale.** `PayoutComplianceService` owns ONLY payout-specific gates (G13-G18). User-role gates (G04+G05+G06) remain `LegalComplianceService` territory. Phase 5 wiring at `routers/payouts.py:create_payout` invokes BOTH services:

```python
legal = LegalComplianceService(session)
payout = PayoutComplianceService(session)
gate_results = await legal.check_gates_for_user_role(current_user, role="owner")
gate_results += await payout.check_gates_for_payout_create(current_user, role="owner")
```

Naming convention: methods named `*_payout_*` return ONLY payout-specific gates. G06 is intentionally absent from `_PAYOUT_GATE_CHECKERS` (per O.F — G06 is owner-side, not payout-side).

## Idempotency convention

**Final keying:**

```
payout_request:owner={user_id}:nonce={header_value | uuid4_hex}
```

- Header present → `nonce={header_value}`
- Header absent → `nonce={uuid.uuid4().hex}` (random 32-char hex)

**Fast path (EXISTS-check):**

```python
existing = await session.execute(
    select(PayoutRequest).where(PayoutRequest.idempotency_key == idempotency_key)
)
if (existing_idempotent := existing.scalar_one_or_none()) is not None:
    return PayoutResponse.model_validate(existing_idempotent)
```

**Race-past-EXISTS handler (Marina Q5=(б), uses CL-2 + CL-3):**

```python
try:
    await session.flush()  # CL-1: surface IntegrityError without committing
except IntegrityError as e:
    await session.rollback()
    if extract_constraint_name(e) == IDEMPOTENCY_KEY_CONSTRAINT_NAME:
        # Race-past-EXISTS — UNIQUE collision, idempotent re-read
        existing = await session.execute(
            select(PayoutRequest).where(
                PayoutRequest.idempotency_key == idempotency_key
            )
        )
        return PayoutResponse.model_validate(existing.scalar_one())
    raise  # other constraint — honest re-raise per Q5=(б)
```

**Why strict-distinguish (Q5=(б)) over broad catch.** A broad catch masks unexpected constraint violations (e.g. FK failure surfacing later if router-side validation drifts) by translating them into a misleading "idempotent replay" response. CL-2 + CL-3 make the cost trivial: one constant + one helper module + one comparison. Conservative no-match treatment (helper returns None when constraint name not extractable, e.g. SQLite test environment) defaults to re-raise — safer than guessing.

## CL-1 rationale (flush() instead of commit())

Pre-existing pattern at `routers/payouts.py:194` was:

```python
session.add(payout)
try:
    await session.commit()
except IntegrityError:
    await session.rollback()
    raise HTTPException(409, ...) from e
```

This double-committed: `get_db_session` autocommits on handler success path. The explicit `commit()` was redundant (no-op when paired with autocommit) but blurred the Pattern 1 S-48 contract — same shape as 5b.7a O.4 in bot handler.

**Why `flush()` instead of `commit()` for the strict-distinguish error path:**

1. `flush()` synchronously surfaces UNIQUE collisions (the goal of the try-block) WITHOUT committing the transaction.
2. After `rollback()` on collision, the session is clean — `session.execute(select(...))` for the re-read works inside the same transaction context that `get_db_session` will eventually commit (or rollback if anything else fails downstream).
3. If we kept `commit()`: collision would have rolled back the explicit commit, then `get_db_session`'s autocommit on success path would commit nothing meaningful (re-read happens inside the rolled-back-then-fresh transaction). Functionally identical for happy path, but less honest about session ownership.
4. Pre-flight verified `get_db_session` autocommits on success (`src/api/dependencies.py:170-183`).

This brings router code into Pattern 1 alignment with bot handler (5b.7a fix). No behavior change for successful payout creation; only semantic alignment.

## Test coverage

### Skeleton (test_payout_compliance_service.py — NEW, 7 cases)
1. `test_init_accepts_session` — smoke
2. `test_gates_for_payout_transition_empty_table_raises_value_error` — empty `_PAYOUT_TRANSITION_GATES` table
3. `test_gates_for_payout_create_empty_table_raises_value_error` — empty `_PAYOUT_CREATE_GATES` table
4. `test_check_gate_unmapped_gate_raises_not_implemented` — empty `_PAYOUT_GATE_CHECKERS` registry
5. `test_check_gates_for_payout_transition_propagates_value_error` — ValueError from inner gates_for_* surfaces
6. `test_check_gates_for_payout_create_raises_not_implemented` — by-design NotImplementedError (Phase 5 chooses dispatch path)
7. `test_dispatch_after_monkeypatch_registry` — monkeypatch entry into `_PAYOUT_GATE_CHECKERS` → `check_gate` routes correctly. Proves Option A dispatcher logic is real.

### Idempotency (test_payouts_idempotency.py — NEW, 6 cases)
1. `test_create_payout_with_header_returns_existing_on_replay` — EXISTS-fast-path hit
2. `test_create_payout_no_header_generates_unique_key` — UUID4 fallback distinct keys across 2 POSTs
3. `test_create_payout_idempotency_key_unique_constraint_handles_race` — `flush()` raises IntegrityError(`ix_payout_requests_idempotency_key`) → rollback → re-read returns existing
4. `test_create_payout_other_integrity_error_re_raises_does_not_re_read` — `flush()` raises IntegrityError(`fk_payout_requests_owner_id`) → rollback → re-raise; assert post-rollback re-read NOT called
5. `test_create_payout_idempotency_key_format` — constructed key matches `payout_request:owner=<id>:nonce=<32-hex>` regex
6. `test_create_payout_header_value_used_in_key` — POST with header `abc123` → key contains `nonce=abc123`

### Helper (tests/unit/utils/test_db_errors.py — NEW, 4 cases)
1. `test_extract_constraint_name_asyncpg_style` — `orig.diag.constraint_name` extracted
2. `test_extract_constraint_name_no_orig` — returns None
3. `test_extract_constraint_name_no_diag_attribute` — aiosqlite shape (no diag attr) returns None
4. `test_extract_constraint_name_empty_constraint` — empty string treated as not extractable

### Integration verification
`tests/integration/test_payout_concurrent.py` re-run 3/3 pass — no direct calls to `create_payout` (uses `payout_service.{approve,reject}_request`). O.J pre-flight: zero direct call sites; no signature-change mitigation needed.

## Verification

| Gate | Pre-5b.7b baseline | 5b.7b result |
|---|---|---|
| ruff (`src/`) | 4 | 4 |
| ruff (`src/ + tests/`) | 20 | 20 |
| mypy (`src/`) | 10 | 10 |
| pytest unit (excl. test_main_menu) — 5b.7a baseline | 62 fail / 616 pass / collected 678 | — |
| pytest unit — after 5b.7b.1 | — | 62 fail / 623 pass (+7) |
| pytest unit — after 5b.7b.2 | — | 62 fail / 633 pass (+10 over 5b.7b.1; +17 cumulative) |
| Alembic head | `e6a88faa9fa0` | `e6a88faa9fa0` (untouched) |
| S-48 violations introduced | 0 | 0 (CL-1 removed pre-existing redundant commit; PayoutComplianceService Pattern 1) |

## Deferred to production launch

These items consolidate into the Phase 3 closure batch → `BACKLOG.md` (single packaged commit). NOT inline `BACKLOG.md` commits per CLAUDE.md "Process discipline".

- **Phase 5 `_PAYOUT_GATE_CHECKERS` body fills** — G13/G14 PayoutRequest variants (currently operate on PlacementRequest; FK schema decision deferred); G15/G16 Phase 4 KEP/Мой налог; G17/G18 real provider integration (5b.6 markers swapped for real-now bodies).
- **Phase 5 `_PAYOUT_TRANSITION_GATES` table population** — `(pending → processing)`, `(processing → paid)` etc.
- **Phase 5 `_PAYOUT_CREATE_GATES` table population** — likely `frozenset({G13, G14, G17, G18})` per Marina policy.
- **Phase 5 wiring at `routers/payouts.py:create_payout`** — invoke BOTH `LegalComplianceService.check_gates_for_user_role(user, "owner")` AND `PayoutComplianceService.check_gates_for_payout_create(user, "owner")`. Single-line addition each.
- **`check_gates_for_payout_create` dispatch design (O.I)** — Phase 5 chooses: (a) parallel user-keyed checker registry vs (b) draft PayoutRequest construction.
- **`PayoutRequest.placement_id` FK** — schema change to link payout to its placement; required for G13/G14 PayoutRequest variants if Phase 5 picks dispatch path (b) above.
- **`payout_service.create_payout` dead code cleanup (re-surfaces 5b.7a O.2 / Marina Q7=(b))** — dead since v4.2 router-side path duplicates simpler version. Production-prep cleanup; if Phase 5 revives, NDFL/NPD/velocity/cooldown logic preserved.
- **`payout_service.create_payout` S-48 violation O.H** — `async with session.begin()` at `payout_service.py:513` violates Pattern 1 ("MUST NOT poison sessions with active autobegin"). Dormant (zero callers). Phase 5 revival must refactor.
- **Frontend `addPayout` X-Idempotency-Key opt-in (O.G)** — `web_portal/src/api/payouts.ts:11` doesn't send header. Backend ships safe-by-default (UUID4 fallback) but frontend network-retry doubles. One-line opt-in change. Out of 5b.7b backend charter.
- **YooKassa Payouts API mapping (O.A)** — YooKassa requires `Idempotence-Key` header ≤64 chars. Our key shape reaches ~70 chars. Phase 5 designs mapping (separate key, hash, or shortened prefix). Skeleton key is internal — YooKassa key is external; they don't have to be identical.
- **G06 provider-validated state (re-surface 5b.7a Deferred)** — current 5b.7a body checks "valid record exists in DB"; Phase 5 swaps with provider integration (YooKassa Payouts recipient-check, SBP, BIK, OAuth).

## Lessons (for Phase 3 closure batch — NOT inline BACKLOG)

- **L26** — Skeleton with populated dispatchers (Option A) over all-NotImplementedError stubs: Phase 5 cost reduction (additive registry inserts only); architectural commitment honest (structure shipped, not just API). Test surface today is meaningfully larger (monkeypatch dispatch verification proves dispatcher logic is real). Use Option A when (a) sibling precedent exists with populated dispatcher pattern AND (b) registry shape is reasonably committable for Phase N+1.
- **L27** — Service partition via naming convention (Q6 partition (c)): `PayoutComplianceService.*_payout_*` returns ONLY payout-specific gates; user-role gates remain `LegalComplianceService` territory. Caller-side composition (Phase 5 wiring invokes BOTH services) is simpler than has-a (composition embedding) or duplicate (G04 bodies in two registries). No circular delegation; clean boundaries; future readers don't have to chase cross-service dispatch.
- **L28** — IntegrityError strict-distinguish (Q5=(б)) over broad catch: more honest reporting (FK violations don't masquerade as idempotent replays); test infrastructure cost is small (mock-based unit tests + real-PG integration via testcontainers). Conservative no-match treatment (helper returns None on extraction failure → caller re-raises) defaults to safer behavior than guessing.
- **L29** — Skeleton signature impedance documented (O.I): `check_gates_for_payout_create` raises NotImplementedError as design boundary, NOT workaround. Phase 5 dispatch-path freedom documented inline in service docstring + Deferred section. Surface "this method's body is intentionally Phase N+1 territory" via NotImplementedError + design rationale comment, not via TODO.
- **L30** — `tests/integration/test_payout_concurrent.py` direct-call check (O.J): generalizable pre-flight pattern для FastAPI Header dependency additions. Before changing `Annotated[..., Depends/Header(...)]`, search for direct call sites in tests; add explicit `x_*=None` if needed. (5b.7b case: zero direct calls — no mitigation needed.)
- **L31** — Single source of truth for DB constraint names (CL-2): module-level constant in model file next to column declaration. Tests AND production import. Migration rename → one place to update. Pattern для any UNIQUE/FK constraint inspected at runtime (idempotency_key here; future patterns могут extend if schema introspection grows).
- **L32** — Driver-API divergence helpers (CL-3): asyncpg vs aiosqlite IntegrityError shapes differ. Encapsulate via narrow-purpose helper module; return None on extraction failure; conservative no-match treatment by caller. Avoid inline `getattr` chains in business logic — they hide the driver-API coupling. Helper docstring documents which driver shapes it supports.
- **L33** — P4 once-correctly cleanups bundled in active sub-block: threshold rule — if cleanup is in same module being touched AND verification cheap (~1 pre-flight check) AND cleanup IS proper-fix (not workaround), bundle. If spans new modules with non-trivial risk OR requires separate STOP gate — defer. 5b.7b CL-1/CL-2/CL-3 all satisfied threshold (router being touched anyway, helper in isolated namespace, constant in same model file). 5b.7b is the model — future cleanups can reference this rule.

## Out of scope (deferred to Phase 5 / future sub-blocks)

- **Phase 5 body fills** — `_PAYOUT_GATE_CHECKERS` / `_PAYOUT_TRANSITION_GATES` / `_PAYOUT_CREATE_GATES` populations. Skeleton ships empty by design.
- **Phase 5 wiring at router** — calling sites for both services in `create_payout`. Skeleton ships unwired by design.
- **`PayoutRequest.placement_id` FK** — schema change; Phase 5 territory (or earlier production-prep sub-block).
- **Dead-code cleanup (Q7 deferred)** — `payout_service.create_payout` / `request_payout_for_placement` / `create_pending_payout`. Re-surfaces from 5b.7a; production-prep batch.
- **Frontend updates** — out of charter; UX flagged in "Deferred to production launch".
- **Channel-add hook (5b.7a closed)** — separate sub-block, separate STOP gate.

## Notes

5b.7b reused 5b.7a precedents:
- `LegalComplianceService` registry + dispatcher pattern (mirrored exactly in `PayoutComplianceService`)
- Pure mocked unit test pattern (`MagicMock(spec=AsyncSession)` + `monkeypatch` on registry dicts)
- Pattern 1 S-48 contract throughout (skeleton service receives session; never commits)
- Single-source-of-truth literals (CL-2 mirrors how `_TRANSITION_GATES` keys are kept in lockstep with `_ALLOW_LIST`)
- AuditLog convention unchanged (no new audit-write surfaces in 5b.7b)

🔍 Verified against: `cbe59bd` | 📅 Updated: 2026-05-03T00:00:00Z
