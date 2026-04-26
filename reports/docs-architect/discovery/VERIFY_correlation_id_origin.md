# VERIFY — `correlation_id` origin in `TransitionMetadata`

**Goal:** decide if `correlation_id: str | None = None` stays in the
`TransitionMetadata` schema (alignment commit § 2.B.0 point 5). Read-only
research.

**Verdict:** **STUB-IN-DOCSTRING.** Keep the field as `Optional[str] = None`,
mark in docstring as "reserved for Phase 3 request-tracing wiring; populated
by middleware when introduced." No source today, but cost of keeping the
field is one line and a comment.

---

## Middleware setting `correlation_id` / `request.state.correlation_id`?

**No.**

```
$ grep -rn "correlation_id\|request.state.correlation\|x-correlation" src/api/middleware/
(no matches)
```

Registered middleware:
- `src/api/middleware/audit_middleware.py` — reads `request.state.user_id`
  and `request.state.user_aud` (set by the auth dep `_resolve_user_for_audience`
  in `src/api/dependencies.py`). Does **not** set or read any
  `correlation_id`.
- `src/api/middleware/log_sanitizer.py` — referenced as middleware in
  `audit_middleware.py` docstring; no `correlation_id` interaction either.

Post-Phase-1 §1.B.0b refactor (PF.4) explicitly removed an unsafe JWT
re-decode in `audit_middleware`. That refactor introduced
`request.state.user_id`, but did **not** introduce `correlation_id`.

---

## Existing consumers in `src/`?

**No.**

```
$ grep -rn "correlation_id" src/
(no matches)

$ grep -rn "correlation_id" web_portal/src/ mini_app/src/
(no matches)
```

Zero references across backend and both frontends. There is no upstream
producer (middleware, auth dep, tracing instrumentation) and no downstream
consumer (logger formatter, Sentry integration, audit log column).

---

## Is there a standard FastAPI/Starlette mechanism in play?

`Sentry` SDK in `src/tasks/sentry_init.py` uses its own trace propagation
(`sentry-trace` / `baggage` headers) but does not surface a UUID into
`request.state`. No `BackgroundTasks`, no `ContextVar`, no
`fastapi.middleware.cors`-adjacent tracing layer is registered.

So today: no field on the request, no field on the audit log, no logger
filter, no header convention. The model field would be unset on every
transition.

---

## Why STUB-IN-DOCSTRING (not DROP, not KEEP)

| Option | Cost | Pro | Con |
|---|---|---|---|
| **KEEP** silently | low | forward-friendly | misleading — implies a field is filled in, but nothing fills it |
| **STUB-IN-DOCSTRING** | low | forward-friendly + explicit | none material |
| **DROP** | low | YAGNI; no orphan field | re-adding later means a Pydantic schema change to `TransitionMetadata` and a snapshot regeneration |

`TransitionMetadata` is a closed `extra="forbid"` Pydantic model
(consolidation report §5). Adding/removing fields after Phase 2 ships is a
contract change that ripples into `tests/unit/test_contract_schemas.py`
snapshots. Keeping the field as `Optional[str] = None` with explicit
docstring text is cheaper than a future schema bump and clearer than a
silent KEEP.

---

## Recommended schema text

```python
class TransitionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # ...

    correlation_id: str | None = None
    """Request-scoped UUID for tracing a single user action across log /
    Sentry / audit_log / placement_status_history.

    RESERVED — no producer wired in Phase 2. Phase 3 plan: request-id
    middleware sets `request.state.correlation_id` (uuid4 if absent in
    `X-Request-Id` header), the FastAPI dependency that constructs
    `TransitionMetadata` reads it through, and the logger filter / Sentry
    `before_send` mirror it. Until Phase 3 lands, callers leave this
    None and the schema remains stable.
    """
```

Phase 3 wiring plan (out of Phase 2 scope, captured here so the field's
docstring is not a vague promise):

1. New middleware `correlation_id_middleware.py`: reads `X-Request-Id`
   header or generates `uuid4()`, sets `request.state.correlation_id`,
   echoes it back in response header.
2. `src/api/dependencies.py` exposes `get_correlation_id(request)` → `str`.
3. The router-level dependency that builds `TransitionMetadata` injects it.
4. Celery-driven transitions inherit `None` (no request) — that's correct
   semantics, scheduler runs are outside any request.

---

## Ancillary finding (not a question, just observation)

`audit_logs` table has no `correlation_id` column today either. If Phase 3
wiring goes in, the column should land in the same migration so that
`audit_logs.correlation_id` and `placement_status_history.correlation_id`
(the future history table) join cleanly. Capture in plan-08 backlog under a
new ticket if the user agrees with STUB-IN-DOCSTRING.

---

🔍 Verified against: `b8c54e2` (main HEAD) | 📅 Updated: 2026-04-26
