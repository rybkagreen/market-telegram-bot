---
name: docs-sync
description: MUST BE USED for post-change documentation updates and sprint changelog sync. Generates incremental discovery reports and Keep-a-Changelog formatted entries. Use after any code change, merge, or milestone completion.
---

# Docs & Changelog Sync Standard

## 🔒 CRITICAL RULE: DOCUMENTATION & CHANGELOG SYNC
This is an absolute constraint. A task is considered **INCOMPLETE** if the blocks below are not updated.

### 🔄 After EVERY code change (handler, model, service, config, migration)
1. Update `/reports/docs-architect/discovery/` using the template:
   - `CHANGES_<YYYY-MM-DD>_<short-desc>.md`
   - Record: affected files, business logic impact, new/changed API/FSM/DB contracts, migration references
   - Include: `🔍 Verified against: <commit_hash> | 📅 Updated: <ISO8601>`
2. Do NOT rewrite old files — only incremental append or targeted edits.
3. If change spans multiple domains → create one unified file.

### 🏁 After SPRINT completion (feature-set, milestone, merge to main)
1. Update `CHANGELOG.md` in project root using Keep a Changelog standard:
   - `## [Unreleased]` → move to `[vX.Y.Z] - <YYYY-MM-DD>`
   - Sections: `Added`, `Changed`, `Fixed`, `Removed`, `Breaking`, `Migration Notes`
   - Include ticket/commit links, affected modules, rollback commands
2. Sync version in `pyproject.toml` and `mini_app/package.json` (if API/Mini App contract changed).

⚠️ FAILURE TO UPDATE = TASK INCOMPLETE. Do not finalize response without completing this step.

---

## Discovery Report Template (`/reports/docs-architect/discovery/CHANGES_*.md`)

```markdown
# Change Discovery: <short-description>
**Date**: <YYYY-MM-DD>
**Commit**: `<short_hash>`
**Trigger**: <feature/bugfix/refactor/migration>

## 📁 Affected Files
| Path | Change Type | Reason |
|------|-------------|--------|
| `src/...` | MODIFIED | ... |

## 🧠 Business Impact
- ...

## 🔄 Contract Changes
- **API**: `GET /...` → ...
- **FSM**: `StateA` → `StateB` ...
- **DB**: Migration `<alembic_rev>`: ...

## 📎 Verification
- [ ] Code matches docs
- [ ] No drift with QWEN.md / PROJECT_MEMORY.md
- [ ] AAA structure preserved

🔍 Verified against: `<commit>` | 📅 Updated: `<ISO8601>`
```

## CHANGELOG.md Template

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...

### Breaking
- ...

### Migration Notes
```bash
alembic upgrade head
make lint && make typecheck
```

## [vX.Y.Z] - YYYY-MM-DD
### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...

### Breaking
- ...

### Migration Notes
```bash
alembic upgrade head
```
```

## Rules
- Keep entries atomic. One feature/fix → one section.
- Use imperative mood: "Add...", "Fix...", "Remove..."
- Link tickets/commits: `#123`, `abc123f`
- Never leave `[Unreleased]` empty after merge.
- Cross-reference QWEN.md version header with CHANGELOG latest version.
