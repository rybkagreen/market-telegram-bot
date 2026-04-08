---
name: docs-sync
description: Use after any code change to create CHANGES_*.md and update CHANGELOG.md per INSTRUCTIONS.md
---

# docs-sync skill

When invoked (via /docs-sync or automatically after task completion), perform:

## 1. Create discovery file
Path: `reports/docs-architect/discovery/CHANGES_<YYYY-MM-DD>_<short-desc>.md`

Template:
```
# Changes: <short-desc>
**Date:** <ISO8601>
**Author:** Claude Code
**Sprint/Task:** <task name>

## Affected Files
- `path/to/file.py` — <what changed and why>

## Business Logic Impact
<describe impact on flows, if any>

## API / FSM / DB Contracts
<new or changed contracts; "none" if not applicable>

## Migration Notes
<alembic revision or "none">

---
🔍 Verified against: <git rev-parse --short HEAD> | 📅 Updated: <ISO8601>
```

## 2. Update CHANGELOG.md
- Add entry under `## [Unreleased]`
- Format: `- <type>: <description> (<file(s)>)`
- Types: Added | Changed | Fixed | Removed | Breaking

## 3. Output validation checklist
- [ ] CHANGES_*.md created at correct path
- [ ] CHANGELOG.md [Unreleased] updated
- [ ] No contradictions with QWEN.md / CLAUDE.md / INSTRUCTIONS.md
- [ ] All claims reference specific files/lines

End with: `🔒 Docs & Changelog synced. Task complete.`
