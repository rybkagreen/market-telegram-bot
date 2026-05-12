# CHANGES — BL-080 8a Provider unification + DI

**Date:** 2026-05-12
**Branch:** `feature/bl080-8a-provider-unification`
**Base:** develop @ `0ea5e99` (post-v0.6.0 followup)

## Closes

- **BL-074 T3.17** — yandex provider skeleton dedup
- **BL-080 T3.18 absorbed** — `_global_provider` DI refactor

## Resolves (from BL-080 probe surprises)

- **S1** — Celery workers running skeleton when `ORD_PROVIDER=yandex` (launch-blocker)
- **S2** — Import-time crash on `ORD_PROVIDER=yandex` без credentials, plus the
  4-vs-2-arg constructor mismatch that would have surfaced если skeleton were deleted
  without redirecting the call site
- **S3** — `_global_provider` module-import test fragility (RuntimeError at pytest
  collection if `ORD_PROVIDER=yandex` env present без keys)

## Summary

Three structural changes converted the ORD provider lifecycle from a fragile
module-state singleton to a lazy DI factory pattern.

1. `src/core/services/ord_service.py` — replaced module-level `_global_provider`
   (initialized at import via `_init_ord_provider_from_settings()`) with a
   `get_ord_provider()` lazy factory backed by a `_provider_singleton: OrdProvider |
   None` cache. Mirrors the precedent set by `src/api/dependencies.py:get_bot`.
   `OrdService.{get,set}_default_provider` preserved as thin wrappers so the
   `api/main.py` lifespan path keeps working without edits.

2. `src/core/services/ord_service.py` — redirected the `YandexOrdProvider` import
   from the skeleton (`ord_yandex_provider`) to the canonical path
   (`yandex_ord_provider`). Updated `_build_ord_provider_from_settings` to pass
   the full 4-arg constructor (`api_key`, `base_url`, `rekharbor_org_id`,
   `rekharbor_inn`) that the canonical class requires; the skeleton accepted only
   2 args, which is why the previous code path silently kept the wrong class
   alive.

3. `src/tasks/celery_app.py` — extended the `worker_process_init` signal handler
   (which already initialized the per-worker `Bot`) to also pre-warm
   `get_ord_provider()`. With the cache populated before any task runs, every
   Celery worker now binds the canonical provider in its own process — closing
   the gap that the probe's S1 surprise documented.

4. `src/core/services/ord_yandex_provider.py` — **deleted**. The skeleton class
   raised `NotImplementedError` from every method; its only role had been to lose
   the import race против the real class. With no remaining importers (verified
   by `rg --type py 'ord_yandex_provider' src/ tests/` returning empty), the file
   is dead code.

## Files touched

- `src/core/services/ord_service.py` — DI factory + canonical import + 4-arg constructor
- `src/tasks/celery_app.py` — `worker_process_init` extension
- `src/core/services/ord_yandex_provider.py` — DELETED (skeleton)

Tests not modified: pre-flight grep (Шаг 2) confirmed zero test files referenced
`_global_provider` directly; all existing tests import `YandexOrdProvider` from the
canonical `yandex_ord_provider` module, so no fixture rewrite was needed.

## Sub-block status (per BL-080 probe § 8 plan)

- **8a CLOSED** ✓ — provider unification + DI
- **8b PENDING** — status enum (T3.19) + Phase 6.B.3 deterministic logic
- **8c PENDING** — ERID flow hardening (idempotency race-window fix, retry
  refinement, audit trail / correlation_id, failure paths enumeration)
- **8d PENDING** — caption budget impl (legal-gated)

## Baselines (preserved bit-for-bit at every step)

| Gate | Pre-8a (develop `0ea5e99`) | Post-8a (Шаг 4 + CHANGES) |
|---|---|---|
| `make format-check` | 0 errors / 401 files | 0 errors / 400 files (−1 from skeleton delete) |
| `make lint` | 7 errors (BL-024 baseline) | 7 errors (BL-024 baseline) |
| `make typecheck` | 0 errors / 293 files | 0 errors / 292 files (−1 from skeleton delete) |
| `make ci-local` pytest | 1013P / 2S / 0F / 0E | 1013P / 2S / 0F / 0E |
| `ci-local` exit code | 1 (lint baseline) | 1 (lint baseline) |

File-count drops reconcile to the one deletion; pytest count unchanged.

## Not included (per BL-080 § 8 sub-block boundaries)

- Status enum migration `OrdRegistration.status String(20) → Enum` (8b)
- `_build_marked_text` deterministic rewrite + `ord_block_publication_without_erid`
  removal (8b — Phase 6.B.3 plan slot)
- Gate G08 deterministic alignment (8b)
- Idempotency race-window fix (INSERT-before-call pattern, 8c)
- Retry policy refinement / exponential backoff / jitter (8c)
- Audit trail expansion (request/response capture, correlation_id linkage to
  `placement_status_history`) (8c)
- Failure paths enumeration + admin override endpoint (8c)
- Caption budget Option A/B/C/hybrid implementation (8d, legal-gated)
- `BACKLOG.md` updates (batched к Phase 3 closure per project rule — not per
  sub-block)

## Verification traces

**S1 — Celery workers using skeleton:**

`get_ord_provider()` in `ord_service.py` reads `settings.ord_provider`. When
`"yandex"`, it instantiates `YandexOrdProvider` imported from the canonical
`yandex_ord_provider` module — the skeleton module no longer exists on disk.
The Celery `worker_process_init` hook in `src/tasks/celery_app.py` calls
`get_ord_provider()` once per worker, populating the per-process singleton
cache before any task executes. Confirmed by `rg --type py 'ord_yandex_provider'
src/ tests/` returning empty after Шаг 4.

**S2 — skeleton deletion safe:**

Two greps in the Шаг 4 pre-flight (`rg 'from .*ord_yandex_provider'` and `rg
'ord_yandex_provider'`) returned zero matches before the `git rm`. Post-deletion
baselines (format-check 0/400, lint 7, typecheck 0/292, pytest 1013P) confirm
no implicit import path was missed.

**S3 — pytest collection no longer triggers module-import provider init:**

Module-load behavior in the refactored `ord_service.py`: the
`_provider_singleton: OrdProvider | None = None` line is a pure variable
assignment; no provider class is constructed until `get_ord_provider()` is first
called. Pytest collection imports `ord_service` but does not call the factory,
so `ORD_PROVIDER=yandex` with missing credentials would no longer raise at
collection time. Baselines passed throughout Шаги 1-4 without any environment
tweaks.

🔍 Verified against: `feature/bl080-8a-provider-unification` HEAD post-Шаг 4
📅 Updated: 2026-05-12
