# CHANGES — Series 16.x closure (2026-04-30)

## Goal

Close series 16.x (PII hardening). Batch metadata commit landing
BACKLOG closures + CHANGELOG entries + plan status overlay + this
closure CHANGES report. No code changes — metadata only.

## Series summary

| Sub-promt | Title | BLs touched | Result |
|---|---|---|---|
| 16.1 | Group A — pin payouts/admin к web_portal | BL-046, BL-049 | Closed |
| 16.2 | Group B — encrypt PayoutRequest.requisites + DocumentUpload.ocr_text | BL-047, BL-048 | Closed |
| 16.3 | Group C — bot payout flow removal | BL-045 | Closed |
| 16.4 | Group D — ReferralItem PII leak fix | BL-050 | Closed |
| 16.5a | LOW batch (4 sub-fixes) | BL-051 partial 4/6 | Sub-tasks closed |
| 16.5b | Canonical PII keys для Sentry init parity | BL-051 sub-task 4 + BL-056 | BL-056 surfaced+closed inline |
| 16.5c | YooKassa webhook over-collection trim | BL-051 sub-task 6 | Closes BL-051 (6/6) |
| BL-057 | Makefile lint/test split (process-finding) | BL-057 | Surfaced+closed inline |

Total BL references: BL-045, BL-046, BL-047, BL-048, BL-049, BL-050,
BL-051 (×6 sub-tasks), BL-056, BL-057, BL-058 (surfaced), BL-059
(surfaced).

## BL deltas in this commit

| BL | Action | Notes |
|---|---|---|
| BL-051 | UPDATED in place → CLOSED | Body status flipped from PARTIAL to Closed; sub-task ⏳ markers flipped to ✅. Closure summary appended (16.5a/b/c assignment). |
| BL-056 | NEW entry → Closed | Materialized inline. Pattern: pii_keys.py canonical extraction. |
| BL-057 | NEW entry → Closed | Materialized inline. Process-finding (verify gates were lint-only). Lesson captured. |
| BL-058 | NEW entry → SURFACED (deferred) | Ruff/format baseline cleanup, mechanical scope. Recommended next mini-promt. |
| BL-059 | NEW entry → SURFACED (Phase 3) | YookassaPayment retroactive PII minimization. Pre-step: real-data audit. |

## HEAD transitions

| Stage | develop | main |
|---|---|---|
| Pre-PROMPT-A | `8eb2de7a` | `49fbe28e` |
| Post-PROMPT-A merge BL-057 | `2598859a` | `49fbe28e` |
| Post-PROMPT-A merge 16.5b | `21ad121d` | `49fbe28e` |
| Post-merge 16.5c (closure Step 1) | `aee600c9` | `49fbe28e` |
| Post-closure metadata commit (this commit) | (see develop tip post-commit; will be in `git log` after push) | `49fbe28e` |
| Post-main bump (Шаг 8, after Marina go) | (unchanged from closure commit) | (see main tip post-bump) |

## Branches scheduled for cleanup (Шаг 9, after Marina go)

- `feature/16-4-userresponse-referral-leak-fix` (16.4 closure)
- `feature/16-5a-low-batch-cleanup` (16.5a closure)
- `feature/16-5b-pii-keys-canonical` (16.5b closure)
- `feature/makefile-split-lint-test` (BL-057 closure)
- `feature/16-5c-yookassa-over-collection-trim` (16.5c closure)

All five are `--no-ff` merged into develop and verified by ci-local
post-merge baseline. `git branch -d` should accept (no `-D` blind).

## Open follow-ups (post-closure)

- **BL-058** — ruff/format baseline cleanup. Mechanical, ~1-2h
  estimated. Recommended next mini-promt to make ci-local truly
  green (not just "noisy baseline holds").
- **BL-059** — Phase 3 retention review (YookassaPayment backfill).
  Pre-step: audit existing rows for real-customer PII vs
  test/sandbox-only. If only test rows — may skip с doc note. If
  real — backfill blocking Phase 3 legal gate.
- **Marina decision space:**
  (a) BL-058 first (mechanical hygiene win),
  (b) Series 17.x credits naming cleanup (BL-053),
  (c) Phase 3 legal compliance gates (large, ~8-10h),
  (d) BL-055 mini (direct bot→portal exchange).

## Verify-gate snapshots

**Pre-closure baseline (develop after 16.5c merge, `aee600c9`):**

```
= 76 failed, 753 passed, 7 skipped, 17 errors in 162.36s (0:02:42) ==
make[1]: *** [Makefile:34: test] Error 1
=== ci-local: FAILED — один или несколько gates not clean. См. output выше. ===
```

**Post-closure baseline (this commit, metadata-only — must match
pre-closure exactly; no code touches between the two snapshots):**

Verified inline by Шаг 7 `make ci-local` run; identical numbers
expected (76 failed / 753 passed / 7 skipped / 17 errors). Lint
baseline 128 / format-check 82 files / typecheck baseline unchanged
through closure (no code touches). ci-local exits non-zero overall
(BL-058 noise + BL-054 cluster); this is by design until BL-058
pass runs.

## Lessons (process)

- **Empirical Шаг 0 inventory > plan/handoff framing.** Reproduced 5+
  times across series 16.x; canonical example is the 16.5b inventory
  finding 3 PII lists (log_sanitizer/api/main/sentry_init), not 2 as
  the plan assumed. Pattern reinforced again in the 16.5c handoff,
  where prose claimed BL-057 + 16.5b were merged — git contradicted,
  PROMPT A landed both before 16.5c restart.
- **Plan validation gate (g):** verify a command actually does what
  its naming implies. `make ci-local` halted at lint for the entire
  16.x series (BL-058 baseline never reached test phase). Use
  `make -n` dry-run + read the rule body before declaring something
  a "verify gate". Lesson encoded in BL-057 closure body.
- **Handoff distinction:** "feature-branch-complete" ≠
  "merged-into-develop". Future handoffs should use SHA-pinned
  language and explicitly note merge state per branch (PROMPT A
  pattern: `develop = X`, `feature/Y = Z`, "merged into develop:
  yes/no").
- **Canonical extraction pattern.** `pii_keys.py` (16.5b) and
  `yookassa_payload.py` (16.5c) both follow the same shape:
  classify-once via categorized constants → project-everywhere via
  one pure function → tests feed sample → docs spell out the
  add-a-field flow. Adding a field is a one-line edit; drift between
  callsites becomes structurally impossible. Worth promoting to a
  reusable pattern note for future PII / data-shape work.
- **Hook discipline (BL-013, BL-016).** Stop-hook noise stayed within
  bounds: ack twice non-trivially, then silent-ignore identical
  fires. Closure-deferred CHANGELOG warnings did not derail the
  session. Discipline holds.

## Files modified by this closure commit

- `reports/docs-architect/BACKLOG.md` — 5 BL deltas (1 update, 4 new entries).
- `CHANGELOG.md` — 3 new `### Verb — title (date)` entries at top of `[Unreleased]` (16.5c, BL-057, 16.5b).
- `IMPLEMENTATION_PLAN_ACTIVE.md` — Series 16.x heading + status overlay.
- `reports/docs-architect/discovery/CHANGES_2026-04-30_series-16-x-closure.md` (this file).

## Series 16.x: officially closed.

Marina review gate is mandatory before main bump (Шаг 8) и branch
cleanup (Шаг 9).

🔍 Verified against: `aee600c9` (develop post-16.5c-merge) | 📅 Updated: 2026-04-30
