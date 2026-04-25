# PHASE 1 — Research consolidation (1.A) before implementation

**Mode:** research / planning. Branch: `feature/fz152-legal-hardening` (off `develop` at `825eaeb`). No production code modified.

**TL;DR:** Plan §1.B.2 cannot execute as-written — six secondary screens/components import the hooks that the plan calls to delete, build will break. Resolution requires a scope decision before any code is written. Other 1.A areas (backend guard, bridge UI, viewport matrix) are largely clean with three smaller objections (open redirect, dead-code endpoints, e2e-login source param). **STOP — awaiting decisions.**

| Area | Result | Blocker for impl? |
|------|--------|-------------------|
| 1.A.1 — Backend guard scope | **23 endpoints** across 4 files (legal_profile, contracts, acts, document_validation) | No — clean enumeration |
| 1.A.2 — Mini_app strip | Plan as-written **breaks the build**; 6 secondary screens ride on the deleted hooks; LegalProfileView omitted from plan | **YES — needs scope decision** |
| 1.A.3 — Bridge UI | Designed; one **security objection** (open-redirect via `?redirect=`) and one **API gap** (AuthTokenResponse no user data) | No — needs design accept |
| 1.A.4 — Viewport matrix | Already configured exactly: iPhone SE / Pixel 5 / Desktop 1440x900 | No — but `/api/auth/e2e-login` mints only mini_app tokens; needs `source` param to test web_portal happy path |

---

## Возражения и риски (read first)

### O.1 — Plan §1.B.2 is structurally incomplete (BLOCKER)

The plan says delete `mini_app/src/api/legalProfile.ts` and `api/contracts.ts` (and the hook files that wrap them). But these screens — **not on the delete list** — still import those hooks:

| Screen / component | Hook(s) imported | Import line |
|---|---|---|
| `screens/advertiser/AdvertiserFrameworkContract.tsx` | `useContracts`, `useGenerateContract`, `useSignContract`, `useMyLegalProfile` | 8-12 |
| `screens/owner/OwnPayoutRequest.tsx` | `useMyLegalProfile`, `useContracts`, `useSignContract` | 12-13 |
| `screens/advertiser/campaign/CampaignPayment.tsx` | `useContracts` | 10 |
| `screens/common/AcceptRules.tsx` | `useAcceptRules` | 7 |
| `components/KepWarning.tsx` | `useRequestKep` | 3 |
| `screens/common/LegalProfileView.tsx` | `useMyLegalProfile` | 4 |

(Verified by `grep` against the live tree.)

After plan execution as-written: TypeScript build fails on six unresolved imports. This is not a stylistic issue — it's a hard incompatibility.

**Resolution options (need your call):**

- **(A) Heavy strip.** Add the six dependents to the delete list and replace each with a portal-redirect (OpenInWebPortal). This deletes core advertiser/owner flows from mini_app: framework-contract signing, payout request, campaign-pre-payment contract check. **Most aligned with FZ-152 spirit** — mini_app shouldn't be doing contract signing at all. Significant rewrite cost (≈ +6 screens + flow audits).
- **(B) Surgical refactor.** Keep `api/contracts.ts` and the contract hooks; only delete the *PII-exposing* parts (LegalProfile* api + hooks + screens). Contract signing in mini_app stays — but the contract status check is non-PII (just contract_status, contract_type), and PDF download switches to portal-redirect. Smaller diff (≈ keeps 80% of impacted screens working with minor edits). **Conflicts with the §1.B.2 written intent** of deleting `api/contracts.ts` wholesale.
- **(C) Defer scope.** Phase 1 deletes only LegalProfile* surface (3 screens, 1 api module, 1 hook file, 1 store). Contract / Act surface stays in mini_app. Phase 1 still solves FZ-152 for legal-profile (PII core); contracts/acts handled separately. Smallest diff. **Doesn't align with plan**, but is the most conservative path.

I recommend **(A) heavy strip** if you agree FZ-152 means "no PII flows in mini_app, full stop". (B) leaves a half-finished story; (C) leaves contracts containing legal data accessible from mini_app via the PDF endpoint. The user's earlier instruction *"После любых правок ... — docker compose up -d --build nginx api"* implies actually shipping working containers, so a build-broken state is not acceptable.

**LegalProfileView.tsx is also missing from the plan delete list** — it displays inn, bank_account, tax_regime via `useMyLegalProfile()`. Plan oversight; should be deleted regardless of A/B/C choice.

### O.2 — Plan §1.B.4 contradicts PF.4 decision

Plan §1.B.4 says: *"**НЕ править** `audit_middleware.py`. Новый `src/api/middleware/aud_audit_middleware.py`"*. But the agreed PF.4 decision is to refactor in place during §1.B.0b (≈ 21 LOC, deletes the unsafe JWT re-decode, threads `request.state.user_id` through `_resolve_user_for_audience`).

**This is reconciled by the PF.4 decision, but it means:**
- `IMPLEMENTATION_PLAN_ACTIVE.md` §1.B.4 needs to be updated to reflect "refactor in §1.B.0b, no parallel file" *as part of the Phase 1 docs commit*.
- `CLAUDE.md` "NEVER TOUCH (extended list for Claude Code)" includes `src/api/middleware/audit_middleware.py` — needs the same caveat ("removed for Phase 1 §1.B.0b refactor; restore-once-merged status TBD by user"). Without this, the next agent that reads CLAUDE.md will be told never to touch a file that the in-flight phase is touching.

I propose the §1.B.0b commit also edits CLAUDE.md to remove the entry and the plan to reflect the refactor. Confirm.

### O.3 — Open-redirect vulnerability in `TicketLogin` (security)

The proposed bridge URL is `${portal_url}/login/ticket?ticket=...&redirect=/legal-profile`. The portal then `navigate(redirect)` after consume. Without validation, an attacker who can set `redirect` to a full URL (`https://evil.example/`) gets the user to land on the attacker's domain *while authenticated* — classic open-redirect. With auth cookies in the URL fragment / token freshly written to localStorage, this is exfiltration-grade.

**Mitigation (mandatory):** in `TicketLogin`, sanitise `redirect`:
```ts
function safeRedirect(raw: string | null): string {
  if (!raw) return '/'
  // Allow only same-origin relative paths starting with `/` and not `//`
  if (raw.startsWith('/') && !raw.startsWith('//')) return raw
  return '/'
}
```

This must land in §1.B.3 implementation, not as a follow-up. I'll write it that way; flag if you'd rather have an allowlist of paths instead.

### O.4 — Backend dead-code after mini_app strip

Per 1.A.2, after the strip 5 endpoints become unreferenced (no other caller in `web_portal/`, `src/bot/`, or other consumers):

| Endpoint | Reason it goes dead |
|---|---|
| `GET /api/acts/mine` | only `MyActsScreen.tsx` called it |
| `GET /api/acts/{id}` | only `MyActsScreen.tsx` |
| `POST /api/acts/{id}/sign` | only `MyActsScreen.tsx` |
| `GET /api/acts/{id}/pdf` | only `MyActsScreen.tsx` |
| `POST /api/users/skip-legal-prompt` | only `LegalProfilePrompt.tsx` |

Note: the dead-status of acts endpoints assumes web_portal does **not** ship an "Acts" screen. Per the inventory, web_portal has no `acts.ts` API module today — confirmed dead.

**Decision needed:**
- **(D-keep)** Keep all 5 endpoints; add a TODO for Phase 2/3 to wire them into web_portal (acts ARE a real domain entity — acts UI is plausibly needed in portal eventually).
- **(D-remove)** Delete the endpoints + their service code in §1.B.5 (extends Phase 1 scope by ≈ 6-8 files: routers/acts.py, ActService, repos, schemas). Removes dead surface but adds rebuild work later if portal needs them.

I recommend **D-keep + Phase 2 ticket**: act endpoints will need a portal home eventually; ripping them out and re-adding is wasted work. `skip-legal-prompt` is a different beast — it's a one-shot UX hack that's purely mini_app's concern; safe to remove. Mixed verdict: keep `/api/acts/*`, remove `/api/users/skip-legal-prompt` in §1.B.5.

### O.5 — `AuthTokenResponse` lacks user data (UX gap, not a bug)

Phase 0 `AuthTokenResponse` returns only `{access_token, token_type, source}`. After `consumeTicket()`, `TicketLogin` will have a token but no user object. The portal's auth store currently expects both. Two options:

- **(E-fetch)** TicketLogin calls `useMe()` after `setAuth(token, {})` — small extra round-trip, no schema change. Simpler.
- **(E-extend)** Add `user: UserResponse` to `AuthTokenResponse` schema — one snapshot regen, all four token-issuing endpoints carry user object now.

I recommend **E-fetch** — keeps the auth-token contract narrow; user fetch is the right place for user data; adding `user` to AuthTokenResponse extends the surface for no real gain and forces snapshot churn.

### O.6 — `/api/auth/e2e-login` is mini_app-only

`src/api/routers/auth_e2e.py:51` hardcodes `source="mini_app"`. The new spec `legal-profile-requires-web-portal.spec.ts` needs a *web_portal* JWT for the happy-path test (otherwise the 200 path can't be exercised through the auth dependency).

**Resolution:** in §1.B.6 (test infra commit) extend `e2e-login` to accept `source: JwtSource` from the request body, defaulting to `mini_app` for backwards compatibility. One-line schema change + line 51 swap. Add `@pytest.mark.parametrize("source", ["mini_app", "web_portal"])` if needed.

---

## 1.A.1 — Backend guard migration

### Endpoint inventory (verbatim from agent)

23 endpoints to flip to `Depends(get_current_user_from_web_portal)`:

| File | Method | Path | Has PII? |
|---|---|---|---|
| `legal_profile.py` | GET / POST / PATCH | `/api/legal-profile/me` + body | Yes (inn, passport, bank, address, kpp, ogrn) |
| `legal_profile.py` | POST | `/api/legal-profile/scan` | No (returns `{success}`) — but legal-domain |
| `legal_profile.py` | GET | `/api/legal-profile/required-fields` | No — but legal-domain |
| `legal_profile.py` | POST | `/api/legal-profile/validate-inn` | No — but legal-domain |
| `legal_profile.py` | POST | `/api/legal-profile/validate-entity` | Yes (returns inn, name, kpp, ogrn) |
| `contracts.py` | GET / POST / PATCH | (multiple) | PDF endpoints expose full legal profile |
| `acts.py` | GET / POST | (4 endpoints) | PDF endpoints expose legal data |
| `document_validation.py` | GET / POST / DELETE | (5 endpoints) | OCR-extracted inn, name, kpp, ogrn |

**Outliers (no change):**
- `GET /api/contracts/platform-rules/text` (contracts.py:234) — currently public, no auth dep. Leave.
- `GET /api/ord/{placement_request_id}`, `POST /api/ord/register` (ord.py) — no PII in response, both audiences valid. Leave.
- `GET /video/{session_id}` (uploads.py) — video metadata, no PII. Leave.

### Test impact

`tests/integration/test_api_legal_profile.py` overrides `app.dependency_overrides[get_current_user]`. After the switch this becomes `[get_current_user_from_web_portal]`. Single fixture update at line 13/51 — straightforward.

Schema snapshots unchanged (auth dep is transparent to Pydantic models).

---

## 1.A.2 — Mini_app strip surface

### Confirmed deletion targets (assuming option **A — heavy strip**, recommended)

**Screens (8):** `LegalProfileSetup.tsx`, `LegalProfilePrompt.tsx`, `LegalProfileView.tsx`, `ContractDetail.tsx`, `ContractList.tsx`, `MyActsScreen.tsx` + matching `.module.css` siblings.

**API modules (2):** `mini_app/src/api/legalProfile.ts`, `mini_app/src/api/contracts.ts`.

**Hook files (2):** `mini_app/src/hooks/useLegalProfileQueries.ts`, `mini_app/src/hooks/useContractQueries.ts`.

**Stores (1):** `mini_app/src/stores/legalProfileStore.ts` (verified zero importers).

**Type identifiers in `mini_app/src/lib/types.ts` (13):** `LegalStatus`, `TaxRegime`, `ContractType`, `ContractRole`, `ContractSignatureInfo`, `ContractStatus`, `SignatureMethod`, `OrdStatus`, `LegalProfile`, `LegalProfileCreate`, `Contract`, `OrdRegistration`, `RequiredFields`. Keep User-side flags (`legal_status_completed`, `legal_profile_prompted_at`, `has_legal_profile`) — they're booleans/timestamps, no PII.

**App.tsx routes (6):** `/legal-profile-prompt`, `/legal-profile`, `/legal-profile/view`, `/contracts`, `/contracts/:id`, `/acts`.

### Coupled secondary changes (the part the plan misses)

Under **option A**, these screens need refactoring or replacement with `OpenInWebPortal` redirects:

- **`AdvertiserFrameworkContract.tsx`** → replace whole screen with `<OpenInWebPortal target="/contracts/framework" />` placeholder. The framework-contract signing flow lives in portal.
- **`OwnPayoutRequest.tsx`** → similar; payout-request requires legal profile. Replace with `OpenInWebPortal target="/payout/request" />`.
- **`CampaignPayment.tsx`** → the contract-presence check via `useContracts()` is the *gate* before payment. Without it, advertiser can pay without framework contract signed → backend rejection. Two options: (a) keep the check via a new non-PII endpoint `GET /api/contracts/has-framework` returning `{signed: bool}`, (b) move the gate to the backend (server-side reject in payment intent). Option (b) is cleaner — gate-on-server is more reliable than gate-on-client. Add as §1.B.5 small task.
- **`AcceptRules.tsx`** uses `useAcceptRules()` for `POST /api/contracts/accept-rules`. Accepting platform rules is **not PII** — it's just a flag. Two options: (a) move accept-rules out of `contracts.ts` into a non-PII module like `api/rules.ts` and keep this flow in mini_app, (b) refactor to a different non-PII endpoint. Option (a) is mechanical and preserves UX. After it: AcceptRules also navigates to `/legal-profile-prompt` on line 41 — change to `navigate('/')` since the prompt screen is gone.
- **`KepWarning.tsx`** uses `useRequestKep()` — KEP request triggers email-driven workflow that requires PII (legal entity details). Replace with `<OpenInWebPortal target="/contracts/kep-request" />`.
- **`LegalProfilePrompt.tsx`** uses `useSkipLegalPrompt()` — but the screen itself is being deleted. The endpoint becomes dead (per O.4). The "skip prompt" UX moves to portal or just disappears.

### Coupled bot changes

`src/bot/handlers/shared/legal_profile.py` (line 59) already directs users to `{settings.web_portal_url}/legal-profile`. **No bot change needed.**

### Forbidden-pattern grep additions to `scripts/check_forbidden_patterns.sh`

```bash
# FZ-152: PII names must not appear in mini_app
if grep -rE 'legalProfile|DocumentUpload|passport_|inn_|snils_|contract_|legal_act' \
    mini_app/src --include='*.tsx' --include='*.ts' > /dev/null; then
  echo "FAIL: PII references in mini_app/"
  exit 1
fi

# FZ-152: legal/contract/act routes must not exist in mini_app App.tsx
if grep -E "'(legal-profile|contracts|acts)" mini_app/src/App.tsx > /dev/null; then
  echo "FAIL: legal routes still registered in mini_app/App.tsx"
  exit 1
fi

# FZ-152: mini_app types.ts must not declare LegalProfile/Contract/Act types
if grep -E '^(export\s+)?(type|interface)\s+(LegalProfile|Contract|Act|Passport|TaxRegime|LegalStatus)' \
    mini_app/src/lib/types.ts > /dev/null; then
  echo "FAIL: legal types still declared in mini_app types.ts"
  exit 1
fi
```

### Deletion order (option A, executable)

1. Land §1.B.5 backend stub `GET /api/contracts/has-framework` (or move gate to server in CampaignPayment flow).
2. Update `App.tsx` routes — remove the 6 lazy imports + 6 route entries.
3. Replace `AdvertiserFrameworkContract.tsx`, `OwnPayoutRequest.tsx`, `KepWarning.tsx` content with `<OpenInWebPortal target="..." />`.
4. Move accept-rules out of `api/contracts.ts` → new `api/rules.ts` with `acceptPlatformRules()` and `useAcceptRules` re-targeted; update `AcceptRules.tsx` redirect target.
5. Modify `CampaignPayment.tsx` to use the new framework-check endpoint (or rely on server-side gate).
6. Delete the 8 screens listed above + their `.module.css`.
7. Delete `api/legalProfile.ts`, `api/contracts.ts`, `hooks/useLegalProfileQueries.ts`, `hooks/useContractQueries.ts`, `stores/legalProfileStore.ts`.
8. Prune 13 type identifiers from `lib/types.ts`.
9. `make lint` / `tsc --noEmit` / Playwright local — must be green at each step ≥ step 6.

---

## 1.A.3 — Bridge UI design (TicketLogin + OpenInWebPortal)

Detailed deliverable:

### Web_portal `TicketLogin`
- **Path:** `web_portal/src/screens/auth/TicketLogin.tsx` (new dir + file).
- **Read params:** `useSearchParams()` (react-router-dom present, pattern in `screens/shared/TopUpConfirm.tsx:37`).
- **Sanitise redirect** per O.3.
- **Hook chain:** `useConsumeTicket(ticket)` → on success `setAuth(token, {} as User)` (auth store at `stores/authStore.ts:24-25`, writes localStorage `rh_token`/`rh_user`) → `useMe()` to populate user → `navigate(safeRedirect(redirect))`.
- **Errors:** match `LoginPage.tsx:159-162` Notification pattern. Hardcoded RU strings (no i18n in portal).
- **Route:** `web_portal/src/App.tsx:108`. Recommend `path: '/login/ticket'` (separate route from `/login`, avoids conditional render in LoginPage).

### Web_portal `useConsumeTicket` + `api/auth.ts`
- `web_portal/src/api/auth.ts` exists — append `consumeTicket(ticket: string): Promise<AuthTokenResponse>`.
- `web_portal/src/hooks/useConsumeTicket.ts` — new, `useMutation` calling `consumeTicket`. Pattern from `mini_app/src/hooks/useLegalProfileQueries.ts:20-28`.

### Mini_app `OpenInWebPortal`
- **Path:** `mini_app/src/components/OpenInWebPortal.tsx` (new).
- **Props:** `{ target: string; children?: ReactNode; variant?: 'button' | 'menu' }`.
- **Behaviour:** on click → `useOpenInWebPortal(target).mutate()` → success: `${portal_url}/login/ticket?ticket=${ticket}&redirect=${encodeURIComponent(target)}` → `Telegram.WebApp.openLink(url)` (typing already in `mini_app/src/telegram.d.ts:20`) with fallback `window.open(url, '_blank')`.

### Mini_app `useOpenInWebPortal` + `api/auth.ts`
- `mini_app/src/api/auth.ts` exists — append `exchangeMiniappToPortal(): Promise<TicketResponse>`.
- `mini_app/src/hooks/useOpenInWebPortal.ts` — new, `useMutation` over the api function with `onSuccess` doing the URL build + `openLink`. Toast on error via `useUiStore`.

### Cabinet integration
- `mini_app/src/screens/common/Cabinet.tsx` — add a `MenuButton` entry (after the existing legal-profile section, lines 80-84) calling `useOpenInWebPortal('/legal-profile').mutate()` on click. Wrap in a small component to avoid hook-in-handler pattern.

### Type declarations
- `Telegram.WebApp.openLink` already typed (`mini_app/src/telegram.d.ts:20`). No change.
- `TicketResponse` and `AuthTokenResponse` are server-defined (`src/api/schemas/auth.py`). Add inline TS shapes mirroring those in the new api modules; no central type file needed.

### Open security item
**O.3 (open redirect)** must be fixed in `TicketLogin` — see "Возражения и риски" above.

---

## 1.A.4 — Frontend tests viewport matrix

### Viewport configuration
`web_portal/tests/playwright.config.ts:43-53` already has the required projects:
```ts
{ name: 'mobile-webkit', use: { ...devices['iPhone SE'] } },
{ name: 'mobile-chromium', use: { ...devices['Pixel 5'] } },
{ name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
```
**No config change required.** The two new specs run on all three projects automatically.

### Auth pattern
Storage state via global setup (`global-setup.ts`). Specs use `test.use({ storageState: role.storageFile })`. The new specs follow the same.

### Ticket-flow JWT minting (the gap — O.6)
- **Mini_app JWT** for negative-path test: existing `e2e-login` works.
- **Web_portal JWT** for positive-path test: `e2e-login` is mini_app-only. **Fix in §1.B.6:** extend `auth_e2e.py` `E2ELoginRequest` schema with `source: JwtSource = "mini_app"`, line 51 reads `source=body.source`. One-line.
- **Consume-able ticket** for `ticket-login.spec.ts`: spec calls `e2e-login` (mini_app) → `exchange-miniapp-to-portal` → use returned ticket. Real bridge end-to-end.

### Backend stand
`docker compose -f docker-compose.test.yml up -d` + `seed_e2e.py` + `ENABLE_E2E_AUTH=true`. Document in spec headers.

### No conflict with BL-001..BL-003
`deep-flows.spec.ts` BL-entries are escrow/dispute/KEP — no overlap with legal-profile auth gating or ticket-login. Safe.

---

## Decisions required before §1.B implementation begins

1. **Mini_app strip scope (O.1)** — A (heavy: also delete 6 secondary screens; replace with OpenInWebPortal placeholders) / B (surgical: keep contracts surface, strip only LegalProfile*) / C (defer: phase 1 = LegalProfile* only, contracts/acts later). **My recommendation: A.**

2. **Plan + CLAUDE.md drift fix (O.2)** — confirm Phase 1 docs commit also (a) edits §1.B.4 of plan to "refactor in §1.B.0b, no parallel file", and (b) removes `audit_middleware.py` from CLAUDE.md NEVER TOUCH.

3. **Open-redirect fix in TicketLogin (O.3)** — confirm `safeRedirect()` allowlist (only same-origin paths starting with single `/`) lands as part of §1.B.3.

4. **Dead-code endpoints (O.4)** — keep `/api/acts/*` (with Phase 2 portal-wire ticket) + remove `POST /api/users/skip-legal-prompt` in §1.B.5? Or different split?

5. **AuthTokenResponse user data (O.5)** — E-fetch (TicketLogin calls useMe after setAuth) or E-extend (add user to AuthTokenResponse, regen snapshot)? **My recommendation: E-fetch.**

6. **e2e-login source param (O.6)** — extend with optional `source: JwtSource = "mini_app"` in §1.B.6, or use bridge-flow workaround? **My recommendation: extend e2e-login (one-line change).**

Once decisions arrive I will:
- Update `IMPLEMENTATION_PLAN_ACTIVE.md` Phase 1 sections to reflect the scope chosen.
- Order the §1.B commits as: §1.B.0a (426 + WWW-Authenticate) → §1.B.0b (audit middleware refactor) → §1.B.1 (legal-profile guard, 23 endpoints) → §1.B.2 (mini_app strip per option A/B/C) → §1.B.3 (bridge UI) → §1.B.4 (aud audit logging — folded into 0b) → §1.B.5 (dead-code cleanup) → §1.B.6 (test infra: e2e-login source param) → §1.D (cross-cutting: hooks, types, Playwright specs, CONTRIBUTING line, TODO ticket) → §1.C verification gates → merge.

**STOP. Nothing on `feature/fz152-legal-hardening` yet — branch is empty (just off `develop`). Awaiting decisions.**

🔍 Verified against: 825eaeb1f53dee7e8d56e83e3e0e5a4f0e8c9d0a — `develop` HEAD as of branch creation | 📅 Updated: 2026-04-25T08:34:16Z (research session)
