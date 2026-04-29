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


# Python-side architectural invariants (plan: optimized-brewing-music):
# Keep Bot creation centralized and forbid status escalation outside the repo.

PY_FLAGS=(
  -rnP
  --include=*.py
  --exclude-dir=.git
  --exclude-dir=.venv
  --exclude-dir=__pycache__
  --exclude-dir=node_modules
)

# INV-3: Bot(...) is created only in session_factory.py and _bot_factory.py.
# api/dependencies.py uses python-telegram-bot (different SDK) — exempt.
run_check_py() {
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
  hits="$(grep "${PY_FLAGS[@]}" "$@" -e "$pattern" "$path" || true)"

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

# INV-3: aiogram Bot() outside session_factory.py / _bot_factory.py.
run_check_py \
  "no direct aiogram Bot(token=...) outside session_factory.py / _bot_factory.py" \
  '^\s*Bot\(\s*token\s*=' \
  'src' \
  --exclude=session_factory.py \
  --exclude=_bot_factory.py \
  --exclude-dir=tests

# Phase 0 (env-constants-jwt-aud): no hardcoded rekharbor.ru URLs anywhere in
# src/ TypeScript source. Must flow through settings.* or import.meta.env.
# Exceptions:
#   - src/config/settings.py                 — the single source of truth.
#   - src/templates/                          — Jinja templates, Phase 6 work.
#   - src/constants/legal.py                  — static apex-URL messages; moved
#     to render-time in Phase 6 when Jinja pipeline is reworked.
run_check_py \
  "no hardcoded rekharbor.ru URL in src/ (use settings.*)" \
  'https?://[a-zA-Z0-9.\-]*rekharbor\.ru' \
  'src' \
  --exclude=settings.py \
  --exclude=legal.py \
  --exclude-dir=templates \
  --exclude-dir=tests

# Same rule on the TypeScript side — screens/components/hooks must not inline
# a rekharbor.ru URL. Allowed only in the api module and the lib/types shims.
run_check \
  "no hardcoded rekharbor.ru URL in mini_app/src (use import.meta.env)" \
  'https?://[a-zA-Z0-9.\-]*rekharbor\.ru' \
  'mini_app/src' \
  --exclude-dir=lib \
  --exclude-dir=api

run_check \
  "no hardcoded rekharbor.ru URL in web_portal/src (use import.meta.env)" \
  'https?://[a-zA-Z0-9.\-]*rekharbor\.ru' \
  'web_portal/src' \
  --exclude-dir=lib \
  --exclude-dir=api

# Phase 2 § 2.B.2 closure (Decision 7): every placement.status mutation must
# flow through PlacementTransitionService.transition() or
# transition_admin_override(). The service is the only legitimate writer.
# This replaces the previous narrow escrow-only guard — after § 2.B.2a + 2.B.2b
# every direct write outside the service is a regression.
#
# Pattern matches `<ident>.status = PlacementStatus.X` on a single line. RHS
# is restricted to PlacementStatus.* to avoid docstring false positives such
# as `placement.status='escrow' ⇒ ...` in INV invariant comments.
run_check_py \
  "no direct <obj>.status = PlacementStatus.* outside placement_transition_service.py" \
  '\w+\.status\s*=\s*PlacementStatus\.' \
  'src' \
  --exclude=placement_transition_service.py \
  --exclude-dir=tests

# setattr-style status mutation — same rule, different syntax.
run_check_py \
  "no setattr(<obj>, 'status', PlacementStatus.*) outside placement_transition_service.py" \
  "setattr\([^,]+,\s*['\"]status['\"]\s*,\s*PlacementStatus\." \
  'src' \
  --exclude=placement_transition_service.py \
  --exclude-dir=tests

# Decision 4 (T1-3): placement.published_at is set exclusively by
# PlacementTransitionService._sync_status_timestamps. Manual writes elsewhere
# can desync with status transitions.
run_check_py \
  "no manual <obj>.published_at = ... outside placement_transition_service.py" \
  '\w+\.published_at\s*=\s*[^=]' \
  'src' \
  --exclude=placement_transition_service.py \
  --exclude-dir=tests

# Phase 1 §1.B.2 / §1.D — FZ-152 mini_app strip enforcement.
# These checks lock in the legal-data carve-out: mini_app must never
# re-introduce PII screens, hooks, types, or API calls. Re-introducing
# any of them is a fail; the carve-out is one-shot, not a rolling decision.

# Allowed exceptions (each scoped narrowly):
#   - mini_app/src/api/legal-acceptance.ts — non-PII consent endpoint
#     URL `/api/contracts/accept-rules`. Excluded from the URL guard so
#     the legitimate POST stays.

run_check \
  "no PII identifiers in mini_app/src (legalProfile / DocumentUpload / passport_ / inn_ / snils_ / legal_act)" \
  '\b(legalProfile|DocumentUpload|passport_|inn_|snils_|legal_act)' \
  'mini_app/src' \
  --exclude=legal-acceptance.ts \
  --exclude=useLegalAcceptance.ts

# `contract_type` / `contract_status` are non-PII metadata used by admin
# accounting screens (e.g. DocumentRegistry.tsx); broad `contract_` was too
# wide. Stripped PII surface is enforced by the type-name check below.

run_check \
  "no deleted legal/contract/act routes in mini_app/src/App.tsx (kept: legal-profile/view, contracts/framework)" \
  "path:\s*['\"](legal-profile-prompt|legal-profile|contracts|contracts/:id|acts)['\"]" \
  'mini_app/src/App.tsx'

run_check \
  "no PII type identifiers in mini_app/src/lib/types.ts" \
  '^(export\s+)?(type|interface)\s+(LegalProfile|LegalProfileCreate|TaxRegime|LegalStatus|Contract|ContractType|ContractRole|ContractStatus|ContractSignatureInfo|SignatureMethod|RequiredFields|Passport)\b' \
  'mini_app/src/lib/types.ts'

# Промт 15.10 — fee values must consume lib/constants.ts (single source of truth
# mirroring src/constants/fees.py via /api/billing/fee-config endpoint).
# Hardcoded numeric/percentage literals in screen/component code drift from
# the backend constants (TopUpConfirm.tsx:66 was the priority finding).
# Allowed only inside lib/constants.ts itself (the source of truth).

# Numeric literals — clear fee values (0.20/0.80/0.40 are CSS-ambiguous, omitted).
run_check \
  "no hardcoded 0.035 (YooKassa fee) outside lib/constants.ts" \
  '\b0\.035\b' \
  'web_portal/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded 0.035 (YooKassa fee) outside mini_app/src/lib" \
  '\b0\.035\b' \
  'mini_app/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded 0.035 (YooKassa fee) outside landing/src/lib" \
  '\b0\.035\b' \
  'landing/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded 0.015 (service/payout fee) outside web_portal/src/lib" \
  '\b0\.015\b' \
  'web_portal/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded 0.015 (service/payout fee) outside mini_app/src/lib" \
  '\b0\.015\b' \
  'mini_app/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded 0.015 (service/payout fee) outside landing/src/lib" \
  '\b0\.015\b' \
  'landing/src' \
  --exclude-dir=lib

# String percentages — unambiguous fee labels (no false positives from
# discounts/CSS gradients). Use formatRatePct(YOOKASSA_FEE) / etc instead.
run_check \
  "no hardcoded '3,5%' or '3.5%' string in web_portal/src" \
  '3[.,]5\s*%' \
  'web_portal/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '3,5%' or '3.5%' string in mini_app/src" \
  '3[.,]5\s*%' \
  'mini_app/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '3,5%' or '3.5%' string in landing/src" \
  '3[.,]5\s*%' \
  'landing/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '1,5%' or '1.5%' string in web_portal/src" \
  '1[.,]5\s*%' \
  'web_portal/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '1,5%' or '1.5%' string in mini_app/src" \
  '1[.,]5\s*%' \
  'mini_app/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '1,5%' or '1.5%' string in landing/src" \
  '1[.,]5\s*%' \
  'landing/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '78,8%' or '78.8%' string in web_portal/src" \
  '78[.,]8\s*%' \
  'web_portal/src' \
  --exclude-dir=lib

run_check \
  "no hardcoded '21,2%' or '21.2%' string in web_portal/src" \
  '21[.,]2\s*%' \
  'web_portal/src' \
  --exclude-dir=lib

echo ""
if [[ "$FAIL" -ne 0 ]]; then
  echo "FAIL: forbidden pattern(s) detected ($CHECK_COUNT checks ran)."
  exit 1
fi

echo "OK: $CHECK_COUNT check(s) passed — no forbidden patterns detected."
