# Changes: gitignore-docs-tracking
**Date:** 2026-04-09T00:00:00+00:00
**Author:** Claude Code
**Sprint/Task:** chore — expose docs-architect/discovery and CLAUDE.md to remote repo

## Affected Files
- `.gitignore` — reworked `reports/` exclusion from `reports/` (directory block) to `reports/*` + negation chain, enabling git traversal into subdirectories; removed `CLAUDE.md` from exclusion list
- `CLAUDE.md` — now tracked by git (previously ignored); contains no secrets, safe for public repo
- `reports/docs-architect/discovery/` (25 files) — initial commit of all CHANGES_*.md and discovery summary files into version control

## Business Logic Impact
No runtime behaviour changes. Infrastructure/tooling only:
- All future `CHANGES_*.md` files written to `reports/docs-architect/discovery/` will be visible in the remote repository and syncable with claude.ai.
- `CLAUDE.md` is now available to contributors cloning the repo without a separate out-of-band transfer.

## API / FSM / DB Contracts
none

## Migration Notes
none

---
🔍 Verified against: 38a9a8d | 📅 Updated: 2026-04-09T00:00:00+00:00
