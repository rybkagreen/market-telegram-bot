# VERIFY T2-2 — Is `placement:retry_failed_publication` dead?

**Goal:** decide whether to delete the task in alignment commit (T2-1/T2-2) or
fix the invariant. Read-only research.

**Verdict:** **DEAD.** Delete in alignment commit.

---

## All references found

```
src/tasks/placement_tasks.py:10   — module docstring listing
src/tasks/placement_tasks.py:56   — DEDUP_TTL["retry_failed_publication"] = 600
src/tasks/placement_tasks.py:584  — @celery_app.task(name="placement:retry_failed_publication", queue=QUEUE_WORKER_CRITICAL)
src/tasks/placement_tasks.py:586  — def retry_failed_publication(self, placement_id: int)
src/tasks/placement_tasks.py:604  — asyncio.run(_retry_failed_publication_async(placement_id))
src/tasks/placement_tasks.py:613  — async def _retry_failed_publication_async
docs/AAA-06_CELERY_REFERENCE.md:85 — table row: "On-demand", "Retry once, then final fail"
```

No `.delay`, no `.apply_async`, no direct `retry_failed_publication(...)` call
anywhere in `src/`, `tests/`, `scripts/`, `Makefile`, `docker-compose*.yml`.

---

## Beat schedule

`celery_app.get_beat_schedule()` (lines 130-262) lists 22 entries. None is
`retry_failed_publication`. The closest siblings are `placement-check-*-sla`
and `placement-check-escrow-stuck` — those wire up live recovery. Retry has
no scheduler entry.

**Beat schedule present?** **No.**

---

## Ops invocation

`docs/AAA-06_CELERY_REFERENCE.md:85` calls it "On-demand" with an em-dash for
the schedule column. No accompanying runbook line, no `celery call ...`
example, no `make`-target, no script in `scripts/`. The "on-demand" label
appears aspirational rather than documented procedure.

**Ops invocation found?** **No.**

---

## Last meaningful change

```
7e497b0  2026-03-11  refactor: complete handlers hierarchy restructure (v3.0)
```

Introduced as part of the v3.0 hierarchy refactor; never gained a dispatcher
in any subsequent commit. Body of the function shows it was a forward-
looking placeholder ("Retry once, then final fail" per docstring), wired
into nothing. Sibling commits in 2026-03-11..2026-04-26 touched delete /
escrow / SLA paths — all ignored retry.

**Time-in-tree without dispatcher:** ~6.5 weeks.

---

## Why this matches the T2-1 invariant concern

Even if revived, the body silently violates **INV-1** (Phase 2 design): it
sets `failed → escrow` without checking whether `escrow_transaction_id` was
already cleared by `check_escrow_sla` group A/B/C refunds. The body assumes
the escrow row is intact, but it explicitly may not be — that is the
"already refunded" race the consolidation report flagged.

So the choice is binary:
- (a) **Delete** in alignment PR — and let any future retry path be designed
  inside `PlacementTransitionService.transition()` with the invariant baked
  in from day one.
- (b) **Fix** in alignment PR — non-trivial: must restore-or-skip on
  refunded-case detection, plus add a real dispatcher (or document why
  on-demand is the only path).

(a) is strictly less work and avoids legitimising a known-broken body.

---

## Recommendation

**DEAD — delete.** Alignment commit removes:
- `retry_failed_publication` task (`src/tasks/placement_tasks.py:583-610`)
- `_retry_failed_publication_async` helper (`src/tasks/placement_tasks.py:613-642`)
- DEDUP_TTL entry (line 56)
- Module docstring line (line 10)
- `docs/AAA-06_CELERY_REFERENCE.md:85` row

Phase 2 `transition()` design need not carve out a special case for retry —
it doesn't exist, no caller depends on it, and the PR is cleaner without
it. If retry semantics are wanted post-Phase-2, model them as a new
`failed → escrow` transition gated by `escrow_transaction_id IS NOT NULL`,
designed against the new service rather than retrofitted around a
zombie body.

---

🔍 Verified against: `b8c54e2` (main HEAD) | 📅 Updated: 2026-04-26
