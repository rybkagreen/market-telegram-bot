# CHANGES — B.6.1 CHANGELOG `[Unreleased]` consolidation

**Date:** 2026-05-11
**Branch:** `feature/b6-1-changelog-unreleased`
**Base:** `develop` @ `72ec2a1`
**Author:** Claude Code (executor) / Marina (decision owner)

## Summary

Consolidated B.1–B.5.1 user-facing changes into `CHANGELOG.md` `[Unreleased]`
section. Docs-only commit; no functional code changes. Replaces prior
placeholder `(empty — ready для next workstream)` at lines 8–10.

Title chosen: **"Mediakit feature shipping — owner PDF + advertiser preview (Phase B)"**.
Sections follow Keep a Changelog 1.1.0 convention (Added / Changed / Fixed /
Removed / Notes) per project precedent (v0.5.2, v0.5.0).

## Sub-blocks included

| Sub-block | CHANGES source file |
|-----------|---------------------|
| Pre-cleanup (drop dead `ChannelService` mediakit duplicates) | `CHANGES_2026-05-11_bl-078-precleanup-channelservice-mediakit.md` |
| B.1 — `MediakitService` rewrite + `comparison_service` Pattern 1 | `CHANGES_2026-05-11_bl-078-b1-mediakit-service-rewrite.md` |
| B.2 — owner-only PDF endpoint | `CHANGES_2026-05-11_bl-078-b2-mediakit-pdf-endpoint.md` |
| B.3 — tests + counter refactor | `CHANGES_2026-05-11_bl-078-b3-tests-and-counter-refactor.md` |
| B.3 hotfix — `theme_color=None` crash | `CHANGES_2026-05-11_bl-078-b3-theme-color-hotfix.md` |
| B.4 — web_portal owner download button | `CHANGES_2026-05-11_b4-mediakit-download-button.md` |
| B.5.1 — advertiser-readable mediakit endpoint | `CHANGES_2026-05-11_b5-1-mediakit-advertiser-endpoint.md` |
| B.5 — mini_app advertiser preview screen | `CHANGES_2026-05-11_b5-mediakit-advertiser-preview.md` |

## Files touched (this commit)

- `CHANGELOG.md` — replaced empty `[Unreleased]` placeholder с consolidated
  section (+114 / −1).
- `reports/docs-architect/discovery/CHANGES_2026-05-11_b6-1-changelog-unreleased.md`
  (this file, new).

## Baselines (preserved bit-for-bit)

Identical к develop @ `72ec2a1` (re-verified empirically at Шаг 1 of this
sub-block):

| Gate | Baseline | This commit |
|------|----------|-------------|
| `make format-check` | 0/401 files | 0/401 files |
| `make lint` | 7 errors (BL-024) | 7 errors (BL-024) |
| `make typecheck` | 0 errors / 293 source files | 0 errors / 293 source files |
| `make ci-local` pytest | 0F / 1013P / 2S / 0E | 0F / 1013P / 2S / 0E |
| `make ci-local` exit | 1 (aggregator on lint) | 1 (aggregator on lint) |

Docs-only change cannot regress code gates by construction (touches only
`CHANGELOG.md` + new `CHANGES_*.md`; both outside `src/`, `tests/`, mypy
scope, ruff scope).

## Why this sub-block

Per Phase B implementation plan §6 "docs sweep + ship":

- Centralised user-facing surface from 8 individual CHANGES files into single
  release-coherent `[Unreleased]` section per Keep a Changelog convention.
- Consumer pattern: SemVer tag bumps reference `[Unreleased]` → release
  notes; granular CHANGES files preserve audit trail per change but не
  serve as release-document surface.
- Atomic shipping signal: marks Phase B mediakit feature work as
  release-ready (subject к B.6.2 BACKLOG closeouts + Phase B closure).

## Not included (explicit defers)

Per PROMPT_29 §sub-block-specific prohibitions:

- **BACKLOG.md edits** — `BL-076 T1.2-D1` (un-skip closes naturally;
  marked в CHANGELOG Fixed section), `BL-078` closure, и all BL-082..085
  closeouts deferred к B.6.2.
- **New BL entries** (BL-086 logo resolver, BL-087 theme_color tinting,
  и other follow-ups surfaced в B.5 CHANGES) deferred к B.6.2.
- **`IMPLEMENTATION_PLAN_ACTIVE.md` updates** — defer к phase closure
  batch.
- **Existing CHANGES files in `reports/docs-architect/discovery/`** —
  append-only, не modified здесь.

## Verification

- `git diff --stat CHANGELOG.md`: `+114 / −1`.
- `git status` post-edit: 2 modified/new files (`CHANGELOG.md` +
  this CHANGES file); untracked `.claude/scheduled_tasks.lock` и `backups/`
  preserved as-is (out of scope, never staged).
- Все 4 gates re-run post-edit: numbers bit-identical к Шаг 1 baselines.
- `git rev-parse main` still `e1c31b3` ✓ (L43 invariant preserved at all
  points; this commit lands on `feature/b6-1-changelog-unreleased`, then
  `--no-ff` merged к `develop`. No `main` touch).

## References

- PROMPT_29 — B.6.1 CHANGELOG `[Unreleased]` consolidation.
- Phase A research: `tmp/b6_1_research.md` (CHANGELOG convention inventory,
  per-sub-block surface extraction, draft `[Unreleased]` validation).
- Keep a Changelog 1.1.0: <https://keepachangelog.com/en/1.1.0/>.

🔍 Verified against: feature/b6-1-changelog-unreleased HEAD (post-commit) | 📅 Updated: 2026-05-11
