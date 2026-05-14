#!/bin/bash
# Stop hook — smart CHANGES/CHANGELOG checker.
# Replaces previous prompt-based hook which spammed on every STOP (BL-113).
#
# Semantics:
#  - Silent on read-only stops (clean working tree, already-warned SHA)
#  - Silent on docs-only commits (no code files in HEAD)
#  - Warns ONCE per SHA if code commit lacks CHANGES_*.md
#  - Warns ONCE per SHA if src/api|src/db touched but CHANGELOG not in same commit
#  - State: .claude/state/warned_shas (git-ignored, append-only)
#
# TODO(BL-113-followup): rotate warned_shas file when exceeds 1000 entries.

set -uo pipefail

# Locate repo root from script location
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
cd "$REPO_ROOT" || exit 0

STATE_DIR=".claude/state"
mkdir -p "$STATE_DIR"
WARNED_FILE="$STATE_DIR/warned_shas"
touch "$WARNED_FILE"

# Get HEAD SHA
HEAD_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")
[ -z "$HEAD_SHA" ] && exit 0

# Already warned for this SHA?
if grep -qFx "$HEAD_SHA" "$WARNED_FILE" 2>/dev/null; then
    exit 0
fi

# Uncommitted code changes? Old hook spammed here. New hook stays silent
# (work in progress, warning premature).
if git diff --name-only HEAD 2>/dev/null | grep -qE '\.(py|ts|tsx|js|jsx|sql)$'; then
    exit 0
fi

# Inspect HEAD commit
FILES_IN_HEAD=$(git show --name-only --pretty=format: HEAD 2>/dev/null | grep -v '^$' || true)
CODE_FILES_IN_HEAD=$(echo "$FILES_IN_HEAD" | grep -E '\.(py|ts|tsx|js|jsx|sql)$' || true)

# Docs-only commit — no warning, mark as seen.
if [ -z "$CODE_FILES_IN_HEAD" ]; then
    echo "$HEAD_SHA" >> "$WARNED_FILE"
    exit 0
fi

# Code commit — check for CHANGES doc and CHANGELOG.
WARNINGS=""

HAS_CHANGES=$(echo "$FILES_IN_HEAD" | grep -E '^reports/docs-architect/discovery/CHANGES_' || true)
if [ -z "$HAS_CHANGES" ]; then
    WARNINGS+="⚠️  HEAD commit ${HEAD_SHA:0:7} contains code changes but no CHANGES_*.md in reports/docs-architect/discovery/. Per BL-013, choose: (a) immediate fix-commit, (b) bundle into next natural commit, (c) defer to phase closure."$'\n'
fi

API_OR_SCHEMA=$(echo "$CODE_FILES_IN_HEAD" | grep -E '^src/(api|db/models|db/migrations)' || true)
if [ -n "$API_OR_SCHEMA" ]; then
    CHANGELOG_TOUCHED=$(echo "$FILES_IN_HEAD" | grep -E '^CHANGELOG\.md$' || true)
    if [ -z "$CHANGELOG_TOUCHED" ]; then
        WARNINGS+="⚠️  HEAD commit ${HEAD_SHA:0:7} touches API/schema/migrations but CHANGELOG.md not in same commit. Consider [Unreleased] update if public contract changed."$'\n'
    fi
fi

if [ -n "$WARNINGS" ]; then
    printf '%s' "$WARNINGS"
fi

# Always mark SHA as seen (avoid re-spam).
echo "$HEAD_SHA" >> "$WARNED_FILE"
exit 0
