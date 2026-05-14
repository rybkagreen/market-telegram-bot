# CHANGES 2026-05-14 — BL-113 Stop-hook fix

## Context
Stop-hook in `.claude/settings.json` used `"type": "prompt"` which re-injected
the same instruction on every Stop event. Without state awareness, this caused
infinite re-fire loops when stop was a STOP-marker awaiting user input (not a
post-work stop). Surfaced in BL-107 probe session (~20 identical fires).

## Changes
- **Replaced** Stop hook from `"type": "prompt"` to `"type": "command"`
  invoking new script `.claude/hooks/stop_check_changes.sh`.
- **Added** `.claude/hooks/stop_check_changes.sh` (bash script).
  Semantics:
  - Silent on read-only stops (uncommitted code in progress — no premature
    warning).
  - Silent on already-warned SHAs (state in `.claude/state/warned_shas`).
  - Silent on docs-only commits.
  - Warns once per SHA when code commit lacks CHANGES_*.md.
  - Warns once per SHA when src/api|db/models|db/migrations touched but
    CHANGELOG.md not in same commit.
- **Updated** `.gitignore` to exclude `.claude/state/` (per-machine state).

## Untouched
- PostToolUse ESLint hook (TS/JS auto-fix).
- PreToolUse force-push block hook.

## TODOs
- BL-113-followup: rotate `.claude/state/warned_shas` when exceeds 1000
  entries. Minor, not urgent.

## Test scenarios verified
- (1) Read-only stop: silent
- (2) Docs-only commit: silent
- (3) Code commit без CHANGES: warns once, second-fire silent
- (4) Code commit с CHANGES: silent

🔍 Verified against: 2c7e15e (worktree HEAD pre-commit) | 📅 Updated: 2026-05-14
