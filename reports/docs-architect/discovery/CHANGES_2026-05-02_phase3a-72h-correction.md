# CHANGES — 2026-05-02 — 72h ORD reporting deadline correction (Phase 3a Block 1.5)

## Summary

Phase 3a Block 1.5. Documentation-only correction. Replaces an
unsourced "72h per ФЗ-38" claim — anchored in
`IMPLEMENTATION_PLAN_ACTIVE.md:505` (plan creation 2026-04-25,
commit `867b349`) and propagated 35× into research artifacts and
Block 1 schema comments — with the empirically verified legal
deadline: end of month following publication month
(ФЗ-38 ст. 18.1 + ПП РФ № 1427 от 01.09.2025, ранее ПП № 974).

## Why

Marina question on plan-claimed deadline triggered investigation.
Web-search verification of ФЗ-38 + ПП-974 / ПП-1427 showed actual
legal requirement = 30 calendar days after end of publication month,
not 72 hours. Investigation
(`INVESTIGATION_72H_ORD_2026-05-02.md`) traced 35 occurrences across
8 files to a single plan-line anchor with **zero** code-logic
propagation (no `timedelta(hours=72)`, no `259200`, no `HOURS_72`,
no Celery beat schedule, no constant, no test).

## What changed

### Modified — canonical fix (active surface)

| File | Line(s) | Before → After |
|---|---|---|
| `IMPLEMENTATION_PLAN_ACTIVE.md` | 505 | *"в течение 72ч per ФЗ-38"* → *"до конца месяца, следующего за месяцем публикации; per ФЗ-38 ст. 18.1 + ПП-1427"* |
| `src/db/migrations/versions/0001_initial_schema.py` | 1484–1485 | `# Phase 3: G12 ФЗ-38 72h reporting window tracking.` → `# Phase 3: G12 — ORD reporting deadline = end of month following publication month` + `# (ФЗ-38 ст. 18.1 / ПП-1427).` |
| `src/db/models/ord_registration.py` | 48–49 | identical comment fix to migration |
| `src/core/enums/placement_gate.py` | 38–41 | G12 trailing comment `# ФЗ-38 72h` → `# ORD report by end of next month per ФЗ-38 ст. 18.1 + ПП-1427`; line restructured (parenthesised assignment over multi-line for the comment to fit Ruff E501 with explanation) |

### Modified — ERRATUM headers (frozen historical preservation)

Bodies retained verbatim; only a one-paragraph ERRATUM block prepended
between the existing title block and the body.

- `reports/docs-architect/discovery/PHASE3_RESEARCH_AGENT_B_2026-05-02.md`
- `reports/docs-architect/discovery/PHASE3_RESEARCH_AGENT_D_2026-05-02.md`
- `reports/docs-architect/discovery/PHASE3_RESEARCH_2026-05-02.md`
  (consolidated)

Agents A and C had no substantive ORD-72h hits (per investigation
classification table) and are intentionally not annotated.

### NOT modified — deliberate

- `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-block1-foundation.md` —
  CLAUDE.md "Append-only: never rewrite existing CHANGES_*.md files"
  rule; this CHANGES file IS the correction record.
- DB migration **body** — column types, names, defaults, ordering
  unchanged. Only the inline comment edited. `alembic check`
  remains clean; head still `e6a88faa9fa0`. No new revision.
- ORM model **body** — column declarations unchanged. Only the
  inline comment edited.
- `PlacementGate` enum **values** — `G12_PUBLICATION_REPORTED_TO_ORD`
  name preserved (load-bearing — referenced by `GATE_DISPATCH`
  registry in Phase 3b, by `GateResult.gate` field, by upcoming
  Phase 3d API endpoint, and by snapshot
  `tests/unit/snapshots/gate_result_response.json`). Only the
  trailing comment text edited.
- Code **logic** — zero D-category hits per investigation; no
  behaviour change is possible from a documentation-only commit.
- `tests/` — zero E-category hits per investigation; no fixture or
  assertion edited.
- `BACKLOG.md` — Phase 3 closure batch discipline preserved.
- `CHANGELOG.md` — bundled in Phase 3a Block 4 closure (option (b)
  established at the prep STOP).

## Phase 3b implication

Schema field `deadline_at` semantics:

- **Block 1 (landed):** nullable `timestamptz` column, intent "when
  the reporting deadline expires" — value semantics deferred.
- **Phase 3b (gate-checker impl):** value computed as
  `last_day_of_month(published_at) + INTERVAL '1 month'` (i.e. the
  end of the next calendar month after the month of publication),
  per ФЗ-38 ст. 18.1 / ПП-1427. Concretely, if `published_at` falls
  in any day of October, the deadline is `2026-11-30 23:59:59 +03:00`
  (Russian wall-clock end-of-November). The computation has not yet
  been written; this CHANGES file documents the spec, not its
  implementation.
- Admin queries for breached deadlines retain their stored-column
  perf rationale — the change is purely in the formula, not the
  storage shape.

## Investigation reference

`reports/docs-architect/discovery/INVESTIGATION_72H_ORD_2026-05-02.md`
— full propagation analysis, anchor identification via `git blame`
+ `git log -S "72ч"`, 35-hit classification (A/B/C breakdown), and
the L4 lesson framing.

## L4 lesson — deferred to Phase 3 closure batch

A single plan claim with a `*"per <law>"*` suffix read as a citation,
not a paraphrase. Downstream agents treated it as a verified fact and
propagated it 35× without re-verification — into research artifacts,
into Block 1 schema comments, and into the Block 1 closure CHANGES
file — all within seven days of plan creation.

**Lesson title (proposed for Phase 3 closure batch):**
*"Fact-claim verification protocol for legal/regulatory specifications."*

**Lesson statement:** when the plan asserts a regulatory requirement
with a `per <law>` suffix, the implementing session must obtain at
least one primary source (the law text, the official decree, the
operator's published API spec) and cite it in the CHANGES file
before baking the figure into schema, comments, or behaviour.
Empirical verification is cheap; propagating the wrong figure into
production code is not.

Tracked for Phase 3 closure batch (per Marina Q5 disposition (c)).
**`BACKLOG.md` is intentionally not edited** — closure-batch
discipline preserved.

## Append-only respect

The Block 1 closure CHANGES file
(`CHANGES_2026-05-02_phase3a-block1-foundation.md`) is **untouched**
by this commit. The 72h-incorrect lines it contains remain there as
historical record; this new CHANGES file is the canonical
correction record per the CLAUDE.md "Append-only" rule.

`git diff HEAD~ -- reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-block1-foundation.md`
should be empty across the Block 1.5 commit.

## Verify

- `grep -rn "72h\|72ч" src/ IMPLEMENTATION_PLAN_ACTIVE.md` — 0 hits.
- `grep -l "ERRATUM" reports/docs-architect/discovery/PHASE3_RESEARCH_*.md` — 3 files (B, D, consolidated).
- `grep -L "ERRATUM" reports/docs-architect/discovery/PHASE3_RESEARCH_*.md` — 2 files (A, C — correctly untouched).
- `make lint` — 20 ruff baseline preserved.
- `alembic check` — `No new upgrade operations detected`; head `e6a88faa9fa0` (single).
- `python -c "from src.core.enums.placement_gate import PlacementGate; assert len(list(PlacementGate)) == 18; assert PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD.value == 'G12_PUBLICATION_REPORTED_TO_ORD'"` — clean.
- `pytest tests/unit/test_contract_schemas.py --no-cov` — 23/23 pass.

🔍 Verified against: pending Block 1.5 commit (this commit) | 📅 Updated: 2026-05-02
