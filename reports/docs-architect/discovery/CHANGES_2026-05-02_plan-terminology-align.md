# CHANGES — 2026-05-02 — Plan terminology alignment: `legal_type` → `legal_status` in § 3

## Summary

Phase 3 preparation (docs-only). Aligns the Phase 3 section of
`IMPLEMENTATION_PLAN_ACTIVE.md` with the `legal_status` vocabulary
already used in `src/db/models/legal_profile.py`. Code is **untouched**.

This is the alignment commit required by CLAUDE.md "Plan validation
gate (c)" and surfaced as **CON-1** in
`PHASE3_RESEARCH_2026-05-02.md` § 2.2. Without this commit any
Phase 3 implementation would copy plan vocabulary that does not exist
in code, producing import errors / silent enum mismatches.

## Why

Phase 3 research consolidation surfaced a plan-vs-code terminology
drift that would propagate into implementation:

| Plan (pre-commit) | Code (`LegalStatus` enum) |
|---|---|
| `legal_type` field | `legal_status` field |
| `individual` | `individual` ✓ |
| `self_employed` | `self_employed` ✓ |
| `ie` | `individual_entrepreneur` |
| `llc` | `legal_entity` |
| `G03_ADVERTISER_LEGAL_TYPE_COMPLIANT` (gate name) | gate semantically reads `legal_status` |

Renaming **code** to match the plan would touch 23 fields across
ORM / migration / schema / service / FE / repo / tests / snapshots —
a destructive multi-file operation.

Renaming the **plan** is documentation-only and one commit. Per the
CLAUDE.md "Plan validation gate (c)" rule, this alignment lands as
the first commit on the implementation branch (here: feature/phase3-prep,
to be merged into develop) **before any Phase 3 implementation
commit**, so plan and code reference the same vocabulary.

## What changed

### Modified
- **`IMPLEMENTATION_PLAN_ACTIVE.md`** § 3 only (Phase 3 — Legal
  Compliance Gates, lines ~460-624).

  Substitutions inside § 3 (code/enum contexts only — natural-language
  references to "юр. тип" / "ФЛ/ИП/ООО" / etc. were left as-is where
  they did not denote the code symbol):

  | Where | Old | New |
  |---|---|---|
  | § 3.A Agent A scope | `enum legal_type и его значения (individual, self_employed, ie, llc?)` | `enum legal_status и его значения (individual, individual_entrepreneur, self_employed, legal_entity)` |
  | § 3.A Agent A scope | `обязательны для каждого legal_type` | `обязательны для каждого legal_status` |
  | § 3.A Agent C scope | `legal_type owner` | `legal_status owner` |
  | § 3.B.1 (gate enum) | `G03_ADVERTISER_LEGAL_TYPE_COMPLIANT` | `G03_ADVERTISER_LEGAL_STATUS_COMPLIANT` |
  | § 3.B.1 (G17 note) | `для llc owner — счёт-фактура` | `для legal_entity owner — счёт-фактура` |
  | § 3.B.3 (gate-checker logic) | `legal_type-specific логика` | `legal_status-specific логика` |
  | § 3.B.3 (bullet) | `` `ie` `` | `` `individual_entrepreneur` `` |
  | § 3.B.3 (bullet) | `` `llc` `` | `` `legal_entity` `` |
  | § 3.C (acceptance) | `legal_type-matrix тесты: individual / self_employed / ie / llc` | `legal_status-matrix тесты: individual / individual_entrepreneur / self_employed / legal_entity` |
  | § 3.D (TS types) | `financial/legal_type детали` | `financial/legal_status детали` |
  | § 3.D (mini_app audit) | `ПД + legal_type info` | `ПД + legal_status info` |

  After the edit: `awk 'NR>=460 && NR<=624' IMPLEMENTATION_PLAN_ACTIVE.md
  | grep -E 'legal_type|\bie\b|\bllc\b|LEGAL_TYPE'` returns 0 lines.

### Deliberately untouched
- **All other plan sections** — § 0, § 1, § 2, § 4-§ 7 (lines 1-459
  and 625-end). These contain remaining `legal_type` references
  (lines 184, 258, 915, 1006, 1040) that will be aligned per-phase
  as those phases enter implementation. Out of scope for this
  Phase 3 prep commit.
- **Codebase** — `src/db/models/legal_profile.py`, all routers,
  schemas, services, repos, FE, tests, snapshots. No code touched.

### Gate name decision
The gate identifier in § 3.B.1 was renamed from
`G03_ADVERTISER_LEGAL_TYPE_COMPLIANT` to
`G03_ADVERTISER_LEGAL_STATUS_COMPLIANT`. Rationale: the gate is
defined to check the `legal_status` field — keeping `LEGAL_TYPE` in
the identifier would re-introduce the same drift the alignment
commit is trying to remove. The frozen research artifact
`PHASE3_RESEARCH_2026-05-02.md` retains the old name as a historical
research record; future readers see the alignment commit + this
CHANGES doc as the canonical translation.

## Verify

- `awk 'NR>=460 && NR<=624' IMPLEMENTATION_PLAN_ACTIVE.md
  | grep -nE 'legal_type|\bie\b|\bllc\b|LEGAL_TYPE'` — empty.
- `awk 'NR>=460 && NR<=624' IMPLEMENTATION_PLAN_ACTIVE.md
  | grep -cE 'legal_status|individual_entrepreneur|legal_entity'` —
  ≥ 12 hits across § 3.A, § 3.B.1, § 3.B.3, § 3.C, § 3.D.
- `grep -n legal_type IMPLEMENTATION_PLAN_ACTIVE.md` — only
  out-of-scope sections (lines 184, 258, 915, 1006, 1040).

## References

- **PHASE3_RESEARCH_2026-05-02.md** § 2.2 CON-1 (terminology drift),
  § 4.2 (recommended alignment commit per CLAUDE.md plan validation
  gate), § 4.1 (granular per-gate split).
- **CLAUDE.md** "Plan validation gate (c)" — alignment commit must
  precede implementation.
- **CLAUDE.md** "Cross-artifact reference fabrication (BL-015)" —
  align plan to code, do not fabricate code symbols on the plan side.
- **`src/db/models/legal_profile.py`** — canonical source of
  `legal_status` enum.

## Out of scope

- Other plan sections — aligned per-phase when those phases enter
  implementation.
- Code rename (`legal_status` → `legal_type`) — rejected; would be
  a 23-field destructive op for zero semantic gain.
- Gate-enum implementation in `src/core/enums/placement_gate.py` —
  Phase 3 implementation work; this prep commit fixes vocabulary
  only.

🔍 Verified against: <commit_hash_filled_post_commit> | 📅 Updated: 2026-05-02T00:00:00Z
