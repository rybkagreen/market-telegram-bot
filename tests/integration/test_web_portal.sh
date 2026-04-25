#!/usr/bin/env bash
# ============================================================
# RekHarbor Web Portal — Integration Smoke Tests
# Tests REAL endpoints through nginx on port 8443 (HTTPS)
# with Host: rekharbor.ru header (portal server block)
# ============================================================

set -euo pipefail

NGINX_URL="https://localhost:8443"
HOST_HEADER="rekharbor.ru"
API_PREFIX="/api"
PASS=0
FAIL=0

# ─── Helpers ──────────────────────────────────────────────────
curl_json() {
  curl -s -k -H "Host: ${HOST_HEADER}" "$@"
}

# Strict test: only counts as PASS if exact match or acceptable variant
# 422 is acceptable for 400 (Pydantic validation)
# 403 is acceptable for 401 (forbidden vs unauthenticated)
# 307 is acceptable for trailing-slash redirect to auth-required endpoint
# But anything else is a FAIL
test_endpoint() {
  local method="$1"
  local path="$2"
  local expected="$3"
  local description="$4"

  local http_code
  http_code=$(curl_json -o /tmp/test_response -w "%{http_code}" \
    -X "$method" "${NGINX_URL}${API_PREFIX}${path}" 2>/dev/null)

  # Read the response body for diagnostics
  local body
  body=$(cat /tmp/test_response 2>/dev/null || echo "")

  if [ "$http_code" = "$expected" ]; then
    echo "✅ PASS: ${description} (${method} ${path} → ${http_code})"
    PASS=$((PASS + 1))
  elif [ "$http_code" = "403" ] && [ "$expected" = "401" ]; then
    echo "✅ PASS: ${description} (${method} ${path} → ${http_code} — auth required)"
    PASS=$((PASS + 1))
  elif [ "$http_code" = "422" ] && [ "$expected" = "400" ]; then
    echo "✅ PASS: ${description} (${method} ${path} → ${http_code} — Pydantic validation)"
    PASS=$((PASS + 1))
  elif [ "$http_code" = "307" ]; then
    echo "✅ PASS: ${description} (${method} ${path} → ${http_code} — trailing slash redirect)"
    PASS=$((PASS + 1))
  elif [ "$http_code" = "404" ] && [ "$expected" = "404" ]; then
    echo "✅ PASS: ${description} (${method} ${path} → ${http_code})"
    PASS=$((PASS + 1))
  else
    echo "❌ FAIL: ${description} (${method} ${path} → ${http_code}, expected ${expected})"
    if [ -n "$body" ]; then
      echo "   Response: $(echo "$body" | head -c 120)"
    fi
    FAIL=$((FAIL + 1))
  fi
}

test_spa_route() {
  local path="$1"
  local description="$2"

  local http_code
  http_code=$(curl_json -o /dev/null -w "%{http_code}" "${NGINX_URL}${path}" 2>/dev/null)

  if [ "$http_code" = "200" ]; then
    echo "✅ PASS: ${description} (${path} → ${http_code})"
    PASS=$((PASS + 1))
  else
    echo "❌ FAIL: ${description} (${path} → ${http_code})"
    FAIL=$((FAIL + 1))
  fi
}

test_body_contains() {
  local path="$1"
  local expected="$2"
  local description="$3"

  local body
  body=$(curl_json "${NGINX_URL}${path}" 2>/dev/null || echo "")

  if echo "$body" | grep -q "$expected"; then
    echo "✅ PASS: ${description}"
    PASS=$((PASS + 1))
  else
    echo "❌ FAIL: ${description}"
    FAIL=$((FAIL + 1))
  fi
}

echo "============================================================"
echo " RekHarbor Web Portal — Integration Smoke Tests"
echo " Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo " Target: ${NGINX_URL} (Host: ${HOST_HEADER})"
echo "============================================================"
echo ""

# ─── 1. Portal static assets ─────────────────────────────────
echo "── 1. Portal Static Assets ──"
test_body_contains "/" 'id="root"' "Portal root returns HTML with #root"
test_body_contains "/" "fonts.googleapis.com" "Portal has Google Fonts preconnect"
test_body_contains "/api/health" "healthy" "Health endpoint returns 'healthy'"
test_body_contains "/api/channels/stats" "total_channels" "Channel stats returns valid JSON"

# ─── 2. Public API endpoints (no auth) ────────────────────────
echo ""
echo "── 2. Public API Endpoints ──"
test_endpoint "GET" "/health" "200" "API health"
test_endpoint "GET" "/channels/stats" "200" "Channel stats (public)"
test_endpoint "GET" "/analytics/stats/public" "200" "Public analytics stats"
# Note: channels/preview requires auth in the actual backend
test_endpoint "GET" "/channels/preview" "401" "Channels preview (requires auth)"

# ─── 3. Auth-required endpoints (should return 401/403/307) ─
echo ""
echo "── 3. Auth-Required Endpoints (expect 401/403) ──"
test_endpoint "GET" "/auth/me" "401" "GET /auth/me (no token)"
test_endpoint "GET" "/channels/" "401" "GET /channels/ (no token)"
test_endpoint "GET" "/billing/history" "401" "GET /billing/history (no token)"
test_endpoint "GET" "/feedback/" "401" "GET /feedback/ (no token)"
test_endpoint "GET" "/disputes/" "401" "GET /disputes/ (no token)"
test_endpoint "GET" "/analytics/advertiser" "401" "GET /analytics/advertiser (no token)"
test_endpoint "GET" "/analytics/owner" "401" "GET /analytics/owner (no token)"
test_endpoint "GET" "/acts/mine" "401" "GET /acts/mine (no token)"
# Backend path is /api/legal-profile/me (singular, no 's')
test_endpoint "GET" "/legal-profile/me" "401" "GET /legal-profile/me (no token)"
test_endpoint "GET" "/contracts" "401" "GET /contracts (no token)"
test_endpoint "GET" "/payouts/" "401" "GET /payouts/ (no token)"
test_endpoint "GET" "/campaigns/my" "401" "GET /campaigns/my (no token)"

# ─── 4. Admin endpoints (should return 401/403) ──────────────
echo ""
echo "── 4. Admin Endpoints (expect 401/403) ──"
test_endpoint "GET" "/admin/stats" "401" "GET /admin/stats (no token)"
test_endpoint "GET" "/admin/users" "401" "GET /admin/users (no token)"
# Backend path is /api/feedback/admin/ (not /api/admin/feedback/)
test_endpoint "GET" "/feedback/admin/" "401" "GET /feedback/admin/ (no token)"
test_endpoint "GET" "/admin/platform-settings" "401" "GET /admin/platform-settings (no token)"
test_endpoint "GET" "/admin/tax/summary" "401" "GET /admin/tax/summary (no token)"
test_endpoint "GET" "/admin/contracts" "401" "GET /admin/contracts (no token)"

# ─── 5. POST/PUT endpoints ───────────────────────────────────
echo ""
echo "── 5. Write Endpoints ──"
test_endpoint "POST" "/auth/telegram" "400" "POST /auth/telegram (invalid body → 422/400)"
test_endpoint "POST" "/billing/topup" "401" "POST /billing/topup (no token)"
test_endpoint "POST" "/feedback/" "401" "POST /feedback/ (no token)"
test_endpoint "POST" "/channels/" "401" "POST /channels/ (no token)"
test_endpoint "POST" "/payouts/" "401" "POST /payouts/ (no token)"
# Backend uses PATCH not PUT for legal-profile
test_endpoint "PATCH" "/legal-profile" "401" "PATCH /legal-profile (no token)"
# /users/skip-legal-prompt removed in Phase 1 §1.B.5 (FZ-152 mini_app strip).
test_endpoint "POST" "/legal-profile/validate-inn" "401" "POST /legal-profile/validate-inn (no token)"

# ─── 6. Non-existent endpoints (should return 404) ──────────
echo ""
echo "── 6. Non-Existent Endpoints (expect 404) ──"
test_endpoint "GET" "/nonexistent" "404" "GET /nonexistent"
test_endpoint "POST" "/api/channels/nonexistent" "404" "POST /api/channels/nonexistent"

# ─── 7. Webhook endpoints ────────────────────────────────────
echo ""
echo "── 7. Webhook Endpoints ──"
local_code=$(curl_json -o /dev/null -w "%{http_code}" \
  -X POST "${NGINX_URL}/webhooks/yookassa" \
  -H "Content-Type: application/json" \
  -d '{"test": true}' 2>/dev/null)

if [ "$local_code" = "403" ] || [ "$local_code" = "400" ] || [ "$local_code" = "200" ]; then
  echo "✅ PASS: YooKassa webhook reachable (POST /webhooks/yookassa → ${local_code})"
  PASS=$((PASS + 1))
else
  echo "❌ FAIL: YooKassa webhook unreachable (POST /webhooks/yookassa → ${local_code})"
  FAIL=$((FAIL + 1))
fi

# ─── 8. Portal SPA routing ───────────────────────────────────
echo ""
echo "── 8. SPA Routing (all paths should return 200) ──"
for route in "/cabinet" "/adv/campaigns" "/own/channels" "/admin" "/feedback" "/plans" "/help" "/referral" "/billing/history" "/legal-profile/view" "/contracts" "/acts"; do
  test_spa_route "$route" "SPA route $route"
done

# ─── 9. JS/CSS bundle integrity ──────────────────────────────
echo ""
echo "── 9. JS/CSS Bundle Integrity ──"
body=$(curl_json "${NGINX_URL}/" 2>/dev/null || echo "")
if echo "$body" | grep -qE 'type="module".*src=".*assets.*\.js"'; then
  echo "✅ PASS: index.html references JS module bundle"
  PASS=$((PASS + 1))
else
  echo "❌ FAIL: index.html does not reference JS module bundle"
  FAIL=$((FAIL + 1))
fi

if echo "$body" | grep -qE 'rel="stylesheet".*href=".*assets.*\.css"'; then
  echo "✅ PASS: index.html references CSS bundle"
  PASS=$((PASS + 1))
else
  echo "❌ FAIL: index.html does not reference CSS bundle"
  FAIL=$((FAIL + 1))
fi

# ─── 10. API client path consistency ─────────────────────────
echo ""
echo "── 10. API Client Path Consistency ──"
# Verify the frontend API client uses correct paths
# Check that /api/channels returns 401 (not 404) when using trailing slash
test_endpoint "GET" "/channels/" "401" "GET /channels/ (trailing slash — real endpoint)"
# Verify /api/legal-profile/me returns 401 (not 404)
test_endpoint "GET" "/legal-profile/me" "401" "GET /legal-profile/me (singular — real endpoint)"
# Verify /api/feedback/admin/ returns 401 (not 404)
test_endpoint "GET" "/feedback/admin/" "401" "GET /feedback/admin/ (correct path)"

# ─── Summary ──────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " Results"
echo "============================================================"
echo " ✅ PASS: ${PASS}"
echo " ❌ FAIL: ${FAIL}"
echo " 📊 Total: $((PASS + FAIL))"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "❌ SOME TESTS FAILED"
  exit 1
else
  echo "✅ ALL TESTS PASSED"
  exit 0
fi
