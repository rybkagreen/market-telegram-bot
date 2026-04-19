#!/usr/bin/env bash
#
# check_forbidden_patterns.sh — S-48 grep-guards
#
# Scans the repository for regression patterns that must not re-appear.
# Second line of defence after ESLint (S-46) and the contract-drift snapshot (S-47).
# Exits non-zero on the first violation.
#
# Patterns checked:
#   1. direct `import { api }` inside web_portal screens (bypasses api module)
#   2. legacy field name `reject_reason` in web_portal (backend field is `rejection_reason`)
#   3. phantom path `acts/?placement_request_id`
#   4. phantom path `reviews/placement/`
#   5. phantom path `placements/${...}/start`
#   6. phantom path `reputation/history`
#   7. phantom path `channels/${...}` in direct fetch/axios strings (outside api module
#      and outside navigate() URLs)
#
# Usage:
#   scripts/check_forbidden_patterns.sh
#
# Excluded from search: node_modules, dist, build, .git, .venv

set -euo pipefail

# Resolve repo root = parent of this script's directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Shared grep flags: recursive, with line numbers, PCRE, TS/TSX only,
# skip heavy directories.
COMMON_FLAGS=(
  -rnP
  --include=*.ts
  --include=*.tsx
  --exclude-dir=node_modules
  --exclude-dir=dist
  --exclude-dir=build
  --exclude-dir=.git
  --exclude-dir=.venv
  --exclude-dir=.next
  --exclude-dir=coverage
)

FAIL=0
CHECK_COUNT=0

# run_check <description> <pattern> <path> [extra grep args...]
# Succeeds if grep finds no matches; fails (prints hits) otherwise.
run_check() {
  local desc="$1"
  local pattern="$2"
  local path="$3"
  shift 3

  CHECK_COUNT=$((CHECK_COUNT + 1))

  if [[ ! -e "$path" ]]; then
    echo "  [skip] $desc — path not found: $path"
    return 0
  fi

  local hits
  hits="$(grep "${COMMON_FLAGS[@]}" "$@" -e "$pattern" "$path" || true)"

  if [[ -n "$hits" ]]; then
    echo ""
    echo "  [FAIL] $desc"
    echo "         pattern: $pattern"
    echo "         path:    $path"
    echo "$hits" | sed 's/^/           /'
    FAIL=1
  else
    echo "  [ok]   $desc"
  fi
}

echo "scripts/check_forbidden_patterns.sh — scanning for regression patterns"
echo "repo root: $REPO_ROOT"
echo ""

# 1. Direct `import { api }` in web_portal screens (ESLint backstop).
run_check \
  "no direct 'import { api }' in web_portal/src/screens/**" \
  'import\s*\{\s*api\s*[,}]' \
  'web_portal/src/screens'

# 2. Legacy field name `reject_reason` anywhere in web_portal/src.
run_check \
  "no 'reject_reason' in web_portal/src (use rejection_reason)" \
  '\breject_reason\b' \
  'web_portal/src'

# 3. Phantom path `acts/?placement_request_id`.
run_check \
  "no phantom path 'acts/?placement_request_id' in web_portal/src" \
  'acts/\?placement_request_id' \
  'web_portal/src'

# 4. Phantom path `reviews/placement/`.
run_check \
  "no phantom path 'reviews/placement/' in web_portal/src" \
  'reviews/placement/' \
  'web_portal/src'

# 5. Phantom path `placements/${...}/start`.
run_check \
  "no phantom path 'placements/\${...}/start' in web_portal/src" \
  'placements/\$\{[^}]+\}/start\b' \
  'web_portal/src'

# 6. Phantom path `reputation/history`.
run_check \
  "no phantom path 'reputation/history' in web_portal/src" \
  'reputation/history' \
  'web_portal/src'

# 7. Phantom path `channels/${...}` used as a raw API URL.
#    Allowed:
#      - the canonical api module (web_portal/src/api/channels.ts)
#      - router navigation paths (`/own/channels/${id}/...`, any leading slash/word)
#    Disallowed: fetch/axios/api(`channels/${id}...`) in screens/hooks.
run_check \
  "no raw API path 'channels/\${...}' outside web_portal/src/api/" \
  '(?<![/\w])channels/\$\{' \
  'web_portal/src' \
  --exclude-dir=api

echo ""
if [[ "$FAIL" -ne 0 ]]; then
  echo "FAIL: forbidden pattern(s) detected ($CHECK_COUNT checks ran)."
  exit 1
fi

echo "OK: $CHECK_COUNT check(s) passed — no forbidden patterns detected."
