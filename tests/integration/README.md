# Integration tests — session isolation patterns

## How to run

Integration tests run **on the host** via Poetry, **not** inside the `api`
docker container:

```bash
poetry run pytest tests/integration/ -v
poetry run pytest tests/integration/test_ticket_bridge_e2e.py -v   # single file
```

Reason: the `api` Dockerfile only `COPY src/`, so `tests/` is not present
inside the container, and `/var/run/docker.sock` is not mounted, which means
testcontainers cannot spin up its isolated Postgres from inside `api`. The
host has the Poetry venv (`.venv` → poetry virtualenv, Python 3.14) and the
Docker socket — both prerequisites for the testcontainer fixture.

`docker compose exec api pytest ...` does **not** work today and is tracked
as a Phase 3 backlog item (mount `tests/` into the api image, or add a
test-stage to `docker/Dockerfile.api`). See
`reports/docs-architect/discovery/CHANGES_2026-04-25_phase1-fz152.md` (TODO
ticket section) for the deadline.

## Session isolation patterns

Integration tests in this project run against a real Postgres
testcontainer (see `conftest.py` → `postgres_container`,
`test_engine`). The schema is created once per session; **each test
chooses its isolation strategy based on what the code under test
does with sessions.**

There are three legitimate patterns. Pick the one that matches the
service-under-test's session model — getting it wrong manifests as
either silent state leakage between tests or hangs under
concurrency.

## Pattern A — service accepts session (S-48 contract)

Use the standard `db_session` fixture from `conftest.py`. It opens a
connection, begins a transaction, yields a session bound to that
connection, and rolls back on teardown. The service itself never
opens a session — it operates inside the caller-owned transaction.

**When to use:**
- Service / repository signature is `async def foo(session: AsyncSession, ...)`.
- All mutations route through that `session` argument.

**Reference:** `test_legal_profile_service.py`, `test_contract_service.py`.

## Pattern B — service owns session, **sequential** tests

Use a `bound_factory` fixture that wraps a single connection in an
outer transaction and yields an `async_sessionmaker(bind=connection,
join_transaction_mode="create_savepoint")`. Patch
`async_session_factory` (in both `src.db.session` and the service
module) to point at this factory. Service-internal `async with
session.begin():` becomes a SAVEPOINT inside the outer transaction;
the outer `trans.rollback()` discards everything at test end.

```python
@pytest_asyncio.fixture
async def bound_factory(test_engine):
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        try:
            factory = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            with (
                patch.object(session_module, "async_session_factory", factory),
                patch.object(service_module, "async_session_factory", factory),
            ):
                yield factory
        finally:
            await trans.rollback()
```

**When to use:**
- Service opens its own sessions via `async_session_factory`.
- Tests are sequential (no `asyncio.gather`, no `pytest -n` against a
  single test file's session-owning factories).

**Why not TRUNCATE:**
- O(N) by table count, with `RESTART IDENTITY` masking ordering bugs.
- Cross-test sequence drift made bugs flaky.
- Cannot parallelize: a TRUNCATE in one test wipes the seed of another.
- SAVEPOINT rollback is faster (~30 % on local stack) and isolated by
  construction.

**Reference:** `test_payout_lifecycle.py` (plan-06).

## Pattern C — service owns session, **concurrent** tests

Use a `bound_factory` that binds the sessionmaker directly to
`test_engine` (so each session takes its own connection from the
pool) and TRUNCATE the touched tables in an `autouse` cleanup
fixture.

**When to use:**
- The whole point of the test is to drive `asyncio.gather` /
  multiple coroutines hitting the same row.
- Each coroutine must take its own connection — single-connection
  pattern (B) would serialize them and the race never triggers.

**Why TRUNCATE here:** the service's commits are real (not SAVEPOINT
sub-transactions), so `trans.rollback()` cannot undo them. TRUNCATE
is the only way to clean up between tests. Acceptable cost: the
concurrency suite is small and slow tests are inherent.

**Reference:** `test_payout_concurrent.py` (plan-02 + plan-06).

## Picking between B and C — a quick decision tree

```
  Does the test under test use asyncio.gather / multiple coroutines?
                  │                            │
                 yes                          no
                  │                            │
              Pattern C                    Pattern B
        (engine + TRUNCATE)        (savepoint + auto rollback)
```

Putting a savepoint test under `asyncio.gather` will block on the
single asyncpg connection. Putting a sequential test on the
TRUNCATE pattern works but wastes time and risks order-coupling.

## Common pitfalls

- **Forgetting to patch the service module's `async_session_factory`
  binding.** Patching only `src.db.session` is not enough — Python
  imports are by-reference; the service holds its own reference.
  Patch both.
- **Mixing patterns in a single file.** Easy to do by accident if
  one test is "obviously sequential" and another is "obviously
  concurrent". Split them into separate files: a single fixture per
  file matches the file's intent.
- **`expire_on_commit=True` (the default).** Returned ORM objects
  become detached after commit — `payout.status` reads raise. Always
  pass `expire_on_commit=False` in the test sessionmaker.
- **`session.refresh(obj)` after the outer `trans.rollback()`.** Once
  the transaction is closed, the object's row is gone — refresh
  raises. Read all needed attrs while the transaction is still open.
