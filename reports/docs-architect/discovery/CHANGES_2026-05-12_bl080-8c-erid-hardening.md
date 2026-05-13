# CHANGES — BL-080 8c: ERID flow hardening

**Date:** 2026-05-12
**Branch:** `feature/bl080-8c-erid-hardening`
**Base:** develop @ `e10c1de` (post-8b merge)

## Closes

- **BL-080 8c** — 7 work items per probe § 8

## Resolves (from BL-080 probe surprises)

- **S2** — race-window mitigation through INSERT-pending-row reorder в
  `register_creative` (per probe § 5 recommendation). Combined с Yandex
  deterministic creative IDs (creative-{placement_id} upsert), the gap
  collapses to "row exists but transaction rolled back" which subsequent
  retry resolves via EXISTS-check + provider upsert.
- **S4** — 5 sequential provider calls now wrapped in audit log entries with
  shared correlation_id; partial failures captured as ERROR events bound к
  the registration row.
- **S8** — linear 5-min retries replaced с exponential backoff + jitter via
  `compute_backoff` helper (`src/core/services/ord_retry.py`).
- **8b STOP flag** — `OrdService.set_default_provider` / `get_default_provider`
  wrappers removed; lifespan calls `get_ord_provider()` directly. The
  carryover compat shim из 8a/8b is closed.

## Decisions applied

- **Q3 = (b)** — Exponential backoff + jitter. Hand-rolled (tenacity not in
  deps — adding a dependency for a 20-line helper was unjustified).
- **Q5 = (a)** — Admin override endpoint в this sub-block.
- **Q6 = (a)** — Separate `ord_audit_log` table с SAVEPOINT dual-write
  (mirrors AuditLogRepo precedent at L48).
- **Q7 = (b)** — `correlation_id` column on OrdRegistration. Uses `uuid4`
  (not uuid7) because the field is a join key for a handful of audit entries
  per attempt; the time-ordered B-tree benefit of uuid7 isn't meaningful at
  this grain and stdlib has no uuid7 yet.
- **Q8 = (a)** — Pre-prod migration exception extends к 8c. All schema
  additions inline в `0001_initial_schema.py`; no new Alembic revision.
- **S7 → BL-095** — creative cost reporting deferred к separate BL (out of
  8c scope).

## Summary

ERID flow hardened end-to-end across seven structural changes.

**Schema:** added `ord_audit_log` append-only table + `correlation_id` UUID
column on `OrdRegistration` + `cancelled` value to `ordregistrationstatus`
enum. All inline в `0001_initial_schema.py` per the pre-prod exception. The
`ord_audit_log` table has 4 indices (correlation_id, placement_id,
ord_registration_id, created_at) и uses the existing `ordregistrationstatus`
type для status_from / status_to columns (create_type=False — already created
by ord_registrations.status).

**Idempotency:** `register_creative` now INSERTs the OrdRegistration row in
`pending` state с a fresh correlation_id BEFORE calling the provider. Provider
calls happen in the documented 4-step sequence; на каждом step an
OrdAuditLog entry is dual-written via SAVEPOINT-wrapped `OrdAuditLogRepo.log`.
After successful provider response the row is UPDATEd с the erid + state
transition к `token_received`. On retry, the existing EXISTS-check on the
unique `placement_request_id` short-circuits — combined с Yandex's
deterministic-ID upsert behaviour, double-issuance is impossible in practice.
No `idempotency_key` column added — probe § 5 noted that `placement_request_id`
UNIQUE is functionally equivalent.

**Retry policy:** `compute_backoff(retry_count, base, max, jitter_ratio)` in
`src/core/services/ord_retry.py` computes `min(base × 2^retry, max) × (1 +
random(0, jitter_ratio))`. Applied at 4 Celery retry callsites in
`src/tasks/ord_tasks.py`. `register_creative_task` / `report_publication_task`
use base=5s, max=300s, 5 attempts. `poll_erid_status` uses base=30s,
max=600s, 12 attempts (wider envelope для ERIR async processing).

**Failure paths:** new exception hierarchy в `src/core/exceptions.py`:
`OrdError` → `OrdTransientError` / `OrdPermanentError` →
`OrdProviderRejectedError`. `YandexOrdProvider._request` now raises
`OrdPermanentError` directly on 4xx (no retry waste). The existing
`OrdRegistrationError` was repurposed as `OrdTransientError` subclass so the
5xx/timeout paths preserve their retry behaviour. `_register_creative_async`
catches the two permanent exception types: `OrdProviderRejectedError` routes
к `ord_blocked` status (distinct semantic per Q4=(a)), other
`OrdPermanentError` routes к `erir_failed`. Both write an ERROR audit event.

**Admin override:** `POST /api/admin/ord-registrations/{id}/override` accepts
`{action: "retry"|"cancel", reason: str}`. Retry is allowed from
`ord_blocked` / `erir_failed` / `erir_timeout` — resets к `pending` с a
fresh correlation_id and enqueues `register_creative_task`. Cancel marks the
registration terminal (`cancelled`) with the admin's reason captured.
Invalid source state returns 409; missing reason returns 422; unknown
registration ID returns 404. Both branches write an `admin_override` audit
event с the admin's user_id и reason в payload.

**Wrapper cleanup:** `OrdService.set_default_provider` / `get_default_provider`
deleted (the 8b STOP report flagged them as preserved-for-compat). The
`api/main.py` lifespan now calls `get_ord_provider()` directly — single
source of truth для provider acquisition.

## Files touched (8 commits)

| Шаг | Commit | Files |
|---|---|---|
| 1 | `804fdf6` | `src/db/migrations/versions/0001_initial_schema.py`, `src/db/models/ord_registration.py`, `src/db/models/ord_audit_log.py` (new) |
| 2 | `5464520` | `src/db/repositories/ord_audit_log_repo.py` (new) |
| 3 | `c4407e1` | `src/core/services/ord_service.py` |
| 4 | `f3f4326` | `src/core/services/ord_retry.py` (new), `src/tasks/ord_tasks.py` |
| 5 | `c40c9fb` | `src/core/exceptions.py`, `src/core/services/yandex_ord_provider.py`, `src/tasks/ord_tasks.py`, `tests/unit/test_yandex_ord_provider.py` |
| 6 | `2b108b3` | `src/api/routers/admin.py` |
| 7 | `6a70c58` | `src/api/main.py`, `src/core/services/ord_service.py` |
| 8 | `abca70a` | `tests/unit/test_ord_retry.py` (new), `tests/integration/api/test_admin_ord_override.py` (new) |

## Sub-block status (BL-080 § 8 plan)

- **8a closed** ✓ (provider unification + DI, merged develop @ `7f4e47f`)
- **8b closed** ✓ (status enum + deterministic logic, merged develop @ `e10c1de`)
- **8c closed** ✓ — ERID flow hardening
- **8d pending** — caption budget impl (legal-gated)

## Baselines

| Gate | Pre-8c (develop `e10c1de`) | Post-8c (Шаг 10) |
|---|---|---|
| `make format-check` | 0 errors / 400 files | 0 errors / 405 files (+5: 2 new src + 1 new repo + 2 new tests) |
| `make lint` | 7 errors (BL-024 baseline) | 7 errors (BL-024 baseline) |
| `make typecheck` | 0 errors / 292 files | 0 errors / 295 files (+3 new src files) |
| `make ci-local` pytest | 1018P / 2S / 0F / 0E | **1033P** / 2S / 0F / 0E (+15) |
| `ci-local` exit | 1 (lint baseline) | 1 (lint baseline) |

Шаг 9 stability check: two consecutive ci-local runs each yielded `1033
passed, 2 skipped` (~189s each). No flakiness.

## Not included

- **Caption budget Option A/B/C/hybrid implementation (8d)** — Q1 awaits ОРД
  legal counsel review.
- **Creative cost reporting (BL-095)** — S7 disposition: separate BL.
- **BACKLOG.md updates** — batched к Phase 3 closure per project rule.
- **New Alembic revisions** — pre-prod exception applies through 8c (Q8).
- **Admin UI** for the override endpoint — backend-only deliverable; web_portal
  Cabinet UI can wire to it later (out of 8c scope).

## Verification traces

**Race-window fix:**
- `OrdService.register_creative` step 3 (новое): `INSERT OrdRegistration
  {status=pending, correlation_id=uuid4(), …}` + `session.flush()` makes the
  row visible inside the transaction.
- Steps 4-7: provider calls happen with the registration row already
  identifiable by `placement_request_id` UNIQUE.
- On retry: EXISTS-check (line 116) returns the existing row → short-circuit.
- Yandex deterministic-ID upsert ensures provider-side double-call returns
  the same token, so the residual "row not persisted yet + provider already
  returned" gap collapses на retry.

**Audit log trace:**
- For one successful `register_creative` call: 6 audit entries сare written
  (1 state_transition к pending, 4 provider_request entries, 1
  provider_response, 1 state_transition к token_received). All share the
  same `correlation_id`.

**Retry behaviour trace:**
- `compute_backoff(0, base=5, max=300, jitter=0.3)` → 5-6.5 seconds
- `compute_backoff(3, ...)` → 40-52 seconds
- `compute_backoff(10, ...)` → max-capped at 300-390 seconds

**Admin override trace:**
- `POST /api/admin/ord-registrations/1/override` with body `{"action":
  "retry", "reason": "Yandex outage cleared"}` on a `ord_blocked` registration
  → 200 OK с `{status: "pending", correlation_id: <new UUID>}` + audit log
  entry с `event_type=admin_override` and `payload.action="retry"`.

**Wrapper cleanup trace:**
- `rg 'set_default_provider|get_default_provider' src/ tests/` returns empty.
- `api/main.py` lifespan calls `get_ord_provider()` directly; one eager call
  surfaces misconfiguration at startup.

🔍 Verified against: `feature/bl080-8c-erid-hardening` HEAD post-Шаг 9
📅 Updated: 2026-05-12
