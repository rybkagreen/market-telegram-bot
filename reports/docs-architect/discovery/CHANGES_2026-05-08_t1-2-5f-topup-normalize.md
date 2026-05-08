# T1.2.5f — Topup normalize (Bundle D)

**Branch:** feature/t1-2-5f-topup-normalize
**Started:** 2026-05-08
**Pre-state HEAD:** bb6623b (develop merge base)
**Pre-state baseline:** 0F / 993P / 3S / 0E + 7 lint (conftest) / 0 format / 4 mypy (mediakit)
**Status:** in-progress (commit 6 finalizes)

## Marina decision: Bundle D

Hybrid — placeholder mini_app (LegalProfileView pattern) + full backend pin (BL-046 mirror) + adapted bot regression. Apply payout deeplink pattern (BL-055 / 16.3) к topup flow.

Per-decision summary: see PROMPT_T1_2_5f_PHASE_C.md.

Side-fix α: orphan OwnPayoutRequest.module.css deletion (T1.2.5e leak).
Side-fix β: topup:amount:custom Decimal cast — DEFERRED к BACKLOG.

## Commits

### Commit 1 — `docs(t1.2.5f): create placeholder CHANGES для interleaved updates`
- Hash: <set during commit>
- Files: reports/docs-architect/discovery/CHANGES_2026-05-08_t1-2-5f-topup-normalize.md (NEW)

### Commit 2-6 — TBD

## Deferred to production launch

(filled by commit 6 finalizer)

## Verification footer

(filled by commit 6 finalizer)
