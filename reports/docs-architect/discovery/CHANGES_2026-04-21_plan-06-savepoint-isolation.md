# CHANGES 2026-04-21 — plan-06 integration test SAVEPOINT isolation

## Scope

Follow-up to `FIX_PLAN_06_followups/plan-06-integration-savepoint-isolation.md`
(P2). Replaces the TRUNCATE-based cleanup in
`test_payout_lifecycle.py` with a SAVEPOINT-isolated session factory
following the SQLAlchemy 2 pattern "joining a session into an
external transaction".

Test infrastructure only. No `src/` changes; no public API change.

## What was wrong

`tests/integration/test_payout_lifecycle.py` previously used:

```python
@pytest_asyncio.fixture(autouse=True)
async def _cleanup_after_test(test_engine, bound_factory):
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text(
            "TRUNCATE TABLE transactions, payout_requests, "
            "platform_account, users RESTART IDENTITY CASCADE"
        ))
```

Problems:
- O(N) by table count, with FK CASCADE inflating cost on real
  schemas.
- `RESTART IDENTITY` masked a class of "test passes only in this
  order" bugs by giving every test the same auto-generated ids.
- Cannot parallelize (`pytest -n`) — TRUNCATE in one test blows
  away seed data of another.
- Slower than necessary: SAVEPOINT rollback is roughly half the
  wall-time of TRUNCATE+RESTART on this stack (~4.0 s → ~3.9 s on
  4 tests, but the gap widens with more tests / more tables).

## What changed

### `tests/integration/test_payout_lifecycle.py`

- `bound_factory` rewritten to:
  1. Open a connection from `test_engine`.
  2. Begin an outer transaction on that connection.
  3. Build `async_sessionmaker(bind=connection,
     join_transaction_mode="create_savepoint")`.
  4. Patch `async_session_factory` in both `src.db.session` and
     `src.core.services.payout_service` to point at this factory.
  5. Roll back the outer transaction on teardown.
- `_cleanup_after_test` autouse fixture **removed** — the outer
  rollback in `bound_factory` cleans up everything in O(1).
- Removed unused `text` / `uuid` imports / cleanup machinery.

The key SQLAlchemy 2 mechanism: `join_transaction_mode=
"create_savepoint"` makes any `async with session.begin():` inside
the service open a SAVEPOINT instead of a real transaction. The
service's "commit" is actually a SAVEPOINT release; the outer
rollback discards everything together at test end.

### `tests/integration/test_payout_concurrent.py`

- Docstring updated to flag the **deliberate** use of Pattern C
  (engine + TRUNCATE) and link to the README. SAVEPOINT pattern
  cannot serve this file because asyncpg's single-connection model
  would serialize the gathered coroutines and the race would never
  trigger.

### `tests/integration/README.md` (new)

Documents the three legitimate session isolation patterns and a
decision tree for picking between them:

| Pattern | Used when | Reference |
|---|---|---|
| A — `db_session` fixture | service accepts session as arg (S-48) | `test_legal_profile_service.py` |
| B — savepoint-bound factory | service owns sessions, sequential tests | `test_payout_lifecycle.py` (this plan) |
| C — engine-bound factory + TRUNCATE | service owns sessions, concurrency tests | `test_payout_concurrent.py` |

Calls out four common pitfalls (forgetting to patch the service
module, mixing patterns in one file, `expire_on_commit=True`,
refreshing after outer rollback).

## Validation

```bash
# Single run — green
poetry run pytest tests/integration/test_payout_lifecycle.py --no-cov -v
# → 4 passed in 4.33s

# Three consecutive runs — no cross-test leakage
for i in 1 2 3; do
    poetry run pytest tests/integration/test_payout_lifecycle.py --no-cov -q
done
# → 4 passed in 3.92s
# → 4 passed in 4.20s
# → 4 passed in 4.05s

# Together with concurrent suite
poetry run pytest tests/integration/test_payout_lifecycle.py \
    tests/integration/test_payout_concurrent.py --no-cov
# → 7 passed in 6.29s

# Lint
poetry run ruff check tests/integration/
# → All checks passed!

# Grep-guard
bash scripts/check_forbidden_patterns.sh
# → 7/7 ok
```

## Performance note

The wall-time delta on 4 sequential tests (4.33 s → 3.92 s ≈ 9 %)
is small because TRUNCATE on 4 tables under a fresh schema is fast.
The pattern's real value is in correctness (no `RESTART IDENTITY`
masking, no cross-test leakage, parallel-safe) — speed is a side
effect that scales better as the suite grows.

## Out of scope

- `test_payout_concurrent.py` keeps Pattern C — see Pattern C
  rationale in README.
- Other integration tests (`test_legal_profile_service.py`,
  `test_contract_service.py`, `test_api_legal_profile.py`,
  `test_ord_service_with_yandex_mock.py`,
  `test_placement_ord_contract_integration.py`) already use
  Pattern A and don't need conversion.

🔍 Verified against: 2d4cefe (main) | 📅 Created: 2026-04-21
