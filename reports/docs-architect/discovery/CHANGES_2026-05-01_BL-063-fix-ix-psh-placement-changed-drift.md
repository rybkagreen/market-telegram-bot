# CHANGES — BL-063 fix: ix_psh_placement_changed direction drift

**Date:** 2026-05-01
**Branch:** feat/17-2-clean-sweep-persisted-credits
**BL:** BL-063 (surfaced during 17.2 implementation, alembic check drift on every run)

## Scope

- Model file `src/db/models/placement_status_history.py:69`: amend `Index("ix_psh_placement_changed", "placement_id", "changed_at", postgresql_using="btree")` to use `text("changed_at DESC")` for the second expression, matching applied migration `e6a88faa9fa0:71`.
- Added `text` to the existing `from sqlalchemy import ...` line (file's import convention).
- Migration `e6a88faa9fa0_*.py` NOT touched per migration immutability rule.
- DB schema unchanged — DESC index already exists in production DB (created by the migration when applied).

## Verify

- `alembic check` outputs `No new upgrade operations detected.` (post-fix).
- `ruff check src/db/models/placement_status_history.py` → `All checks passed!`.
- `ruff format --check src/db/models/placement_status_history.py` → `1 file already formatted`.
- `git diff` shows only the 2 expected lines (import + index expression) — no spurious changes.

## Rollback

- `git revert <SHA>` is safe — single-file model amendment with no DB side-effect.
