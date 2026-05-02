# Investigation: 72h ORD reporting deadline origin

**Date:** 2026-05-02
**Branch:** `feature/legal-compliance-gates` @ `f3f16e4`
(prompt expected `9556b49`; HEAD has +1 docs commit `f3f16e4` —
substantive state unchanged for this investigation)
**Trigger:** Marina question on plan-claimed "72h per ФЗ-38" deadline.
Empirical legal verification (web search 2026-05-02) shows ФЗ-38 ст. 18.1
+ Постановление № 974 (с 01.09.2025 — № 1427) prescribe **30 calendar
days after the end of the publication month**, not 72 hours. Marina
does not remember the origin of the 72h figure.

---

## Executive summary

**35 substantive ORD-72h references** across **8 files**, all tracing
back to a single anchor: `IMPLEMENTATION_PLAN_ACTIVE.md:505`,
introduced on 2026-04-25 in commit `867b349` (the very first commit
that added the consolidated implementation plan to the repo). From
that anchor the figure propagated outward in two waves:

1. **Research wave (2026-05-02):** when the four PHASE3 deep-dive
   Explore agents and the consolidator processed the plan, they
   carried the "72h" claim forward verbatim and elaborated on it
   — Agent D especially, with 19 separate reinforcing references
   plus a "Russian legal context" gloss in Agent B that re-asserted
   the figure as if independently verified.
2. **Implementation wave (Block 1, today):** the plan's claim and
   the research artifacts' elaborated version landed together in
   the schema (`deadline_at`, `published_at`), in the
   `PlacementGate` enum trailing comment, in three docstrings, and
   in the Block-1 closure CHANGES file I just wrote.

Zero D-category (code-logic) hits: no `timedelta(hours=72)`, no
`HOURS_72` constant, no `259200` literal, no Celery beat schedule,
no test fixture. The 72h is **documentation- and schema-comment-only
at this point**. Block 1.5 cleanup is therefore mechanical: edit
3 docstrings, edit 1 plan line, edit 1 CHANGES file, decide what to
do with frozen research artifacts.

The factual error is a textbook case of a single unverified
plan claim (single anchor, ~5 LOC of source) generating ~35×
amplification through downstream artifacts — and would have shipped
into the gate-checker semantics in Phase 3b/3c if Marina hadn't
asked. Surfacing as a Phase 3 closure-batch lesson (§ 5).

---

## 1. Total occurrences by category

| Category | Count | Files | Notes |
|---|---:|---:|---|
| **A. Schema docstrings (Block 1 landed)** | 3 | 3 | Mechanical edit |
| **B. Plan / docs claims** | 3 | 2 | Plan line 505 = anchor; my CHANGES file replicates it |
| **C. Research artifacts (frozen historical)** | 29 | 3 | Agent D = 19 ÷ Agent B = 4 ÷ consolidated = 6 |
| **D. Code logic (timedelta, constants, beat)** | 0 | 0 | Confirmed empirical: no `hours=72`, no `259200`, no `HOURS_72` |
| **E. Tests** | 0 | 0 | None |
| **F. Configs** | 0 | 0 | None |
| **G. False positives (filtered out)** | many | many | `oklch(0.72 …)`, line numbers, commit hashes, `post_48h=172800`, baseline counts, `under 72 chars` rule, dispute auto-escalation 72h (separate domain — see § 6 open question 1) |
| **TOTAL substantive** | **35** | **8** | |

---

## 2. Anchor point analysis

### Anchor

**`IMPLEMENTATION_PLAN_ACTIVE.md:505`** — single line:

```
- G12_PUBLICATION_REPORTED_TO_ORD *(в течение 72ч per ФЗ-38)*
```

### git evidence

```
$ git blame -L 505,505 IMPLEMENTATION_PLAN_ACTIVE.md
867b3495 (root 2026-04-25 01:46:26 +0300 505) - G12_PUBLICATION_REPORTED_TO_ORD *(в течение 72ч per ФЗ-38)*

$ git log --all --oneline -p -S "72ч" -- IMPLEMENTATION_PLAN_ACTIVE.md
867b349 docs: add CHANGES reports, CHANGELOG, and consolidated implementation plan
```

`-S "72ч"` returns exactly one commit: the plan-creation commit on
2026-04-25. No subsequent commit added another `72ч` to the plan; no
predecessor introduced it. Plan creation = first appearance of `72ч`
in the repository, full stop.

### Propagation chain (textual cite-chain)

```
IMPLEMENTATION_PLAN_ACTIVE.md:505 (anchor, 2026-04-25)
        │
        │   read by Phase 3 deep-dive agents on 2026-05-02
        ▼
PHASE3_RESEARCH_AGENT_B_2026-05-02.md  ──┐
PHASE3_RESEARCH_AGENT_D_2026-05-02.md  ──┤ (29 hits total)
PHASE3_RESEARCH_2026-05-02.md          ──┘
        │
        │   read by Block 1 implementation on 2026-05-02 (today)
        ▼
src/db/migrations/versions/0001_initial_schema.py:1484
src/db/models/ord_registration.py:48
src/core/enums/placement_gate.py:38
        │
        │   summarised in closure CHANGES file
        ▼
reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-block1-foundation.md:71,73
```

Agents A and C contained zero substantive ORD-72h references; the
amplification came from B (legal-context framing) and D (deepest
ORD-track exposition with concrete schema proposals).

### Why it spread so fast

The plan line uses the assertive idiom *"в течение 72ч per ФЗ-38"*
("within 72 hours per Federal Law 38"). The "per X" suffix reads as
**a citation, not a paraphrase** — a downstream reader reasonably
treats it as a verified fact about Russian advertising law and does
not re-verify. Agent B then wrote *"Russian legal context: ФЗ-38 —
ORD must be notified of publication within 72 hours."* — which reads
like an independent confirmation of the plan, but is in fact a
rephrasing of the same single source. The consolidator
(`PHASE3_RESEARCH_2026-05-02.md`) treated B+D's elaborations as
empirical inputs and wove the figure into "highest-stakes legal gap"
framing (line 221), which then justified the schema columns added in
Block 1.

There is **no second source**. No agent quoted a primary text of
ФЗ-38, no citation of Постановление № 974 / № 1427, no link to the
ORD operator API documentation. The whole chain rests on one
seven-character substring (`72ч per`) in the plan.

---

## 3. Findings by category

### 3.A. Schema docstrings (Block 1 landed) — 3 hits

| File | Line | Snippet |
|---|---|---|
| `src/db/migrations/versions/0001_initial_schema.py` | 1484 | `# Phase 3: G12 ФЗ-38 72h reporting window tracking.` |
| `src/db/models/ord_registration.py` | 48 | `# Phase 3: G12 ФЗ-38 72h reporting window tracking.` |
| `src/core/enums/placement_gate.py` | 38 | `G12_PUBLICATION_REPORTED_TO_ORD = "G12_PUBLICATION_REPORTED_TO_ORD"  # ФЗ-38 72h` |

**Cleanup needed in Block 1.5:** all three are inline comments
referencing the wrong figure. Editing is mechanical (~3 lines, no
schema/migration/model code change required). Note: the column names
themselves (`deadline_at`, `published_at`) remain valid — a deadline
column is the right concept, only its value semantics need to be
re-anchored to the actual ФЗ-38 / ПП-1427 rule (publication month +
30 days).

### 3.B. Plan / docs claims — 3 hits across 2 files

| File | Line | Snippet | Notes |
|---|---|---|---|
| `IMPLEMENTATION_PLAN_ACTIVE.md` | 505 | `- G12_PUBLICATION_REPORTED_TO_ORD *(в течение 72ч per ФЗ-38)*` | **The anchor.** Block 1.5 fix here propagates by reference. |
| `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-block1-foundation.md` | 71 | `Anchors the ФЗ-38 72h reporting window.` | Self-authored today; replicated the schema docstring text. |
| `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-block1-foundation.md` | 73 | `Computed from \`published_at + 72h\` at the registration site (Phase` | Same source. |

The CHANGES file is *not* frozen historical (it was just written
today), so editing it is acceptable. Marina-decision question: is
amending a CHANGES file in-place after creation acceptable, or
should the correction be appended as a follow-up CHANGES note?
Per CLAUDE.md "Append-only: never rewrite existing CHANGES_*.md
files." So Block 1.5 cleanup adds a **new** CHANGES file with the
correction; it does not edit the existing one. (See § 6 open
question 2.)

### 3.C. Research artifacts (frozen historical) — 29 hits

| File | Hit count | Lines |
|---|---:|---|
| `PHASE3_RESEARCH_AGENT_D_2026-05-02.md` | 19 | 27, 143, 274, 285, 288, 289, 295, 297, 314, 392, 412, 434, 480, 482, 505, 526, 532, 544, 565 |
| `PHASE3_RESEARCH_2026-05-02.md` (consolidated) | 6 | 17, 97, 173, 221, 265, 425 |
| `PHASE3_RESEARCH_AGENT_B_2026-05-02.md` | 4 | 216, 218, 220, 464 |

These are deep-dive Explore agent outputs, dated and frozen as a
research record of "what the codebase looked like + what the plan
claimed" at the moment of investigation. Industry practice
(and CLAUDE.md's "research-artifact" framing) treats these as
historical. Editing them rewrites history.

**Recommendation:** keep verbatim, add a single annotation file or
prepend a one-paragraph "ERRATUM" header to the consolidated
artifact (`PHASE3_RESEARCH_2026-05-02.md`) noting that the 72h figure
has been disproved post-research and pointing readers to this
investigation report and the upcoming Block 1.5 cleanup CHANGES file.
This preserves the historical record while ensuring the next reader
does not propagate the error a third time. (See § 6 open question 3.)

### 3.D. Code logic — 0 hits

Verified empirically:
- `grep -rn "hours=72\|HOURS_72\|72\s*\*\s*3600\|259200" src/ tests/` → 0 hits
- `grep -rn "timedelta" src/ tests/ | grep -i "hour"` → all hits use
  `hours=24`, `hours=20`, `hours=48`, never 72.
- No Celery beat schedule entry (`src/tasks/celery_app.py`,
  `src/tasks/celery_config.py` is deleted) references 72h.
- No constant in `src/constants/` references 72h.

The 72h figure has not yet entered any executable path. **This is
the load-bearing finding for Block 1.5 scope:** cleanup is purely
documentation, no logic refactor needed.

### 3.E. Tests — 0 hits

`tests/integration/test_expires_at_consistency.py:7` mentions a
"deadline" in a docstring but in a different domain
(counter-offer payment window). No 72h-related fixture or
assertion anywhere.

### 3.F. Configs — 0 hits

No `.env`, `.env.example`, `pyproject.toml`, `docker-compose*.yml`,
`celery_config.py`, or settings file references 72h.

### 3.G. False positives (filtered)

- **`oklch(0.72 0.18 …)`** — design-system color tokens in
  `web_portal/src/shared/ui/` and a couple of screens. 6+ hits, all
  unrelated.
- **Line numbers ending in `72` / `172` / `272` / `372`** in
  `:172`-style file references inside reports.
- **`172800`** seconds = 48 hours, not 72; appears in
  `src/constants/payments.py` for `post_48h` / `pin_48h` placement
  durations and in the corresponding constants doc/test.
- **Commit hashes containing "72"** (`72c7099`, `7242987`, `72fb7f7`)
  in CHANGES files.
- **Baseline counts** in CHANGES / BACKLOG (`76 failed, 725 passed`
  etc.) where 72/725 happens to contain the digits.
- **`under 72 chars`** in CLAUDE.md commit-message style rule.
- **Dispute auto-escalation 72h** — `web_portal/src/screens/shared/DisputeDetail.tsx:62`,
  `CHANGELOG.md:2013`, `CHANGES_2026-04-21_portal-disputes-deep-audit.md:133`.
  Verified independent: this is a product-UX timeout for stale
  `owner_explained` disputes, not a regulatory deadline. Out of
  scope for this investigation. (See § 6 open question 1 if there
  is desire to verify it independently.)

---

## 4. Block 1.5 cleanup scope recommendation

### Scope estimate: **small**

| Action | Files | LOC |
|---|---|---:|
| Edit 3 schema/code comment lines | `0001_initial_schema.py`, `ord_registration.py`, `placement_gate.py` | ~3 |
| Edit plan anchor line 505 | `IMPLEMENTATION_PLAN_ACTIVE.md` | 1 |
| Add new CHANGES file (correction note, not in-place edit) | `reports/docs-architect/discovery/CHANGES_2026-05-02_phase3a-72h-correction.md` | ~30–50 |
| Optionally: add ERRATUM header to consolidated research | `PHASE3_RESEARCH_2026-05-02.md` | ~5 |
| Update CHANGELOG `[Unreleased]` | `CHANGELOG.md` | ~5 |

**Total active editing:** ~10–15 source-line edits in active files + 1
new CHANGES file + 1 changelog entry. Does **not** touch:
- migration body (column types/names stay; only comment changes)
- model body (column types/names stay; only comment changes)
- enum values (G12 name stays; only trailing comment changes)
- frozen research artifacts (only optional ERRATUM header)
- tests (none affected)

### Replacement text

The corrected legal anchor for the comments and the plan line
should be (suggested wording, Marina to confirm):

> *"per ФЗ-38 ст. 18.1 + ПП РФ № 1427 от 01.09.2025 (предш. ПП № 974)
> — отчёт в ОРД до конца месяца, следующего за месяцем
> публикации"* —
> in code comments, abbreviate to e.g.
> `# G12: ORD reporting deadline = end of next calendar month
> after publication (ФЗ-38 ст. 18.1 / ПП-1427).`

Schema field `deadline_at` semantics: instead of `published_at +
INTERVAL '72 hours'`, compute as
`(date_trunc('month', published_at) + INTERVAL '2 months')` minus
one second, or similar. This is a **logic** correction that lands
in Phase 3b when the gate checker is implemented; Block 1.5 only
fixes documentation, not behaviour.

### What Block 1.5 does NOT do

- Does not change DB schema (no migration edit, no model edit)
- Does not implement the corrected deadline computation
- Does not delete/rewrite frozen research artifacts
- Does not retroactively edit CHANGES_2026-05-02_phase3a-block1-foundation.md
  (append-only rule)

---

## 5. L4-class drift implications (closure-batch lesson)

The plan made an unsourced factual claim *"в течение 72ч per ФЗ-38"*
that empirical legal verification disproves. The claim was treated
as authoritative by four downstream artifacts and propagated
35× into research, schema, code comments, and a closure CHANGES
file — all within one week of plan creation, before any actual
gate-checker behaviour was implemented.

**Lesson for Phase 3 closure batch (proposal):**

> **Fact-claim verification protocol for legal/regulatory
> specifications.** When the plan asserts a regulatory
> requirement with a "per <law>" / "per <regulation>" suffix,
> the implementing session must obtain at least one primary
> source (the law text, the official decree, the operator's
> published API spec) and cite it in the CHANGES file before
> baking the figure into schema, comments, or behaviour. Plan
> claims about Russian advertising / tax / data-protection law
> are **not** self-verifying. Empirical verification is cheap
> (one web search of the legal text) compared to the cost of
> propagating the wrong figure into production code.

Suggest adding this as a new "Plan validation gate (extended,
ad-hoc)" subsection in CLAUDE.md alongside the existing (a)/(b)/(c)
+ extended (d)–(g) checks, scoped to legal/regulatory citations
specifically. Or, more lightly, as a BACKLOG entry tagged
"L4-class drift: regulatory fact-claim". (See § 6 open question 5
for the disposition choice.)

---

## 6. Open questions

1. **Dispute-72h independence.** I treated
   `DisputeDetail.tsx:62` ("Авто-решение, если объяснения нет 72 ч"),
   `CHANGELOG.md:2013` ("Celery auto-escalation для stale
   `owner_explained` диспутов (72h…"), and the dispute audit CHANGES
   as out of scope because they describe a product-UX timeout
   (auto-resolve a dispute when the owner stays silent for 72h),
   not a regulatory deadline. **If this 72h is itself derived from
   the plan-anchor or another unverified source, it should be
   independently audited.** I have not done that audit in this
   investigation.

2. **CHANGES append-only rule.** CLAUDE.md says
   "Append-only: never rewrite existing CHANGES_*.md files." So
   the 72h-incorrect lines I wrote into
   `CHANGES_2026-05-02_phase3a-block1-foundation.md` cannot be
   edited per process. The Block 1.5 cleanup will add a **new**
   correction CHANGES file. Confirm this disposition.

3. **Research artifact handling.** Three options:
   (a) leave verbatim (preserves historical record, but next
       reader may re-propagate);
   (b) prepend an ERRATUM paragraph to the consolidated artifact
       only (`PHASE3_RESEARCH_2026-05-02.md`), pointing to this
       investigation;
   (c) prepend ERRATUM to all three artifacts.
   Recommendation = (b). Marina to confirm.

4. **Plan line 505 fix wording.** I suggest
   *"per ФЗ-38 ст. 18.1 + ПП-1427 — отчёт до конца следующего
   календарного месяца"*. Marina to confirm or replace with the
   wording she prefers (and to verify the ПП-1427 citation, which
   I have only via the prompt, not via my own legal lookup).

5. **L4 lesson disposition.** Three options for §5:
   (a) inline addition to CLAUDE.md "Plan validation gate"
       subsection;
   (b) BACKLOG entry tagged "L4-class drift: regulatory
       fact-claim";
   (c) Phase 3 closure batch only.
   Recommendation = (b) for now (lightweight, doesn't bloat
   CLAUDE.md), with an upgrade to (a) if a second instance of
   the same drift class appears. Marina to confirm.

---

🔍 Verified against: `f3f16e4` | 📅 Updated: 2026-05-02
