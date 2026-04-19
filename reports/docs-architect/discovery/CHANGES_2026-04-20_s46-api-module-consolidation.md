# S-46 API module consolidation — CHANGES

**Branch:** `refactor/s-46-api-module-consolidation`
**Scope:** eliminate all direct `api.*` calls in `web_portal/src/screens/**`,
`web_portal/src/components/**`, and `web_portal/src/hooks/**`. Route every
request through a typed function in `src/api/*` behind a React Query hook in
`src/hooks/*`. Add ESLint guard against regressions.
**Risk:** medium. Touches 14 screens/components/hooks across admin, common,
auth, and shared flows. No behaviour change intended — only indirection.

## Architecture target

```
screen (.tsx) → custom hook (useXQueries.ts) → api module (api/x.ts) → backend
                     ↑
                     React Query
```

Forbidden (enforced by ESLint):
- `import { api } from '@shared/api/client'` in `src/screens/**`, `src/components/**`, `src/hooks/**`
- `api.get/post/put/patch/delete(...)` inside a hook (hooks must call functions exported from `src/api/*`)

## Refactor inventory — 14 call sites removed

### Admin (4 files, 7 direct calls)

| File | Endpoint | Now |
|---|---|---|
| `screens/admin/AdminUserDetail.tsx` | `POST admin/users/{id}/balance` | `useTopupUserBalance()` (new in `useAdminQueries.ts`) + `topupUserBalance()` in `api/admin.ts` |
| `screens/admin/AdminFeedbackDetail.tsx` | `GET feedback/admin/{id}` | `useAdminFeedbackById()` + `getAdminFeedbackById()` |
| `screens/admin/AdminFeedbackDetail.tsx` | `POST feedback/admin/{id}/respond` | `useRespondToFeedback()` + `respondToFeedback()` |
| `screens/admin/AdminFeedbackDetail.tsx` | `PATCH feedback/admin/{id}/status` | `useUpdateFeedbackStatus()` + `updateFeedbackStatus()` |
| `screens/admin/AdminPlatformSettings.tsx` | `GET admin/platform-settings` | `usePlatformSettings()` + `getPlatformSettings()` |
| `screens/admin/AdminPlatformSettings.tsx` | `PUT admin/platform-settings` | `useUpdatePlatformSettings()` + `updatePlatformSettings()` |
| `screens/admin/AdminDisputeDetail.tsx` | `GET disputes/{id}` | `useDisputeById()` (already existed — now used directly) |
| `screens/admin/AdminDisputeDetail.tsx` | `POST disputes/admin/disputes/{id}/resolve` | `useResolveDispute()` (already existed) |
| `components/admin/TaxSummaryBase.tsx` | `GET admin/tax/summary` | `useTaxSummary()` + `getTaxSummary()` |
| `components/admin/TaxSummaryBase.tsx` | `GET admin/tax/kudir/{y}/{q}/{fmt}` (via `fetch`) | `downloadKudir()` helper + `getKudirBlob()` |

### Common (5 files, 9 direct calls)

| File | Endpoint | Now |
|---|---|---|
| `screens/common/AcceptRules.tsx` | `GET contracts/platform-rules/text` | `usePlatformRules()` + `getPlatformRulesText()` |
| `screens/common/AcceptRules.tsx` | `POST contracts/accept-rules` | `useAcceptRules()` (already existed) |
| `screens/common/ContractDetail.tsx` | `GET contracts/{id}` | `useContract()` (already existed) |
| `screens/common/ContractDetail.tsx` | `POST contracts/{id}/sign` | `useSignContract()` (already existed) |
| `screens/common/ContractList.tsx` | `GET contracts/platform-rules/text` | `usePlatformRules()` (same hook as AcceptRules) |
| `screens/common/DocumentUpload.tsx` | `POST legal-profile/documents/upload` | `useUploadDocument()` (new) + `uploadDocument()` in new `api/documents.ts` |
| `screens/common/DocumentUpload.tsx` | `GET legal-profile/documents/{id}/status` | `useUploadStatus()` with `refetchInterval` |
| `screens/common/DocumentUpload.tsx` | `GET legal-profile/documents/passport-completeness` | `usePassportCompleteness()` |
| `screens/common/MyActsScreen.tsx` | `GET acts/mine` | `useMyActs()` (new in `useActQueries.ts`) + `getMyActs()` |
| `screens/common/MyActsScreen.tsx` | `POST acts/{id}/sign` | `useSignAct()` |
| `screens/common/MyActsScreen.tsx` | `GET acts/{id}/pdf` (blob) | `downloadActPdf()` helper + `getActPdfBlob()` |
| `screens/common/Feedback.tsx` | `POST feedback` | `useCreateFeedback()` + `createFeedback()` |

### Auth (2 files, 3 direct calls)

| File | Endpoint | Now |
|---|---|---|
| `screens/auth/LoginPage.tsx` | `POST auth/telegram-login-widget` | `loginWidget()` in new `api/auth.ts` |
| `screens/auth/LoginPage.tsx` | `POST auth/login-code` | `loginByCode()` |
| `components/guards/AuthGuard.tsx` | `GET auth/me` | `getMe()` |

### Hooks (1 file, 1 direct call)

| File | Endpoint | Now |
|---|---|---|
| `hooks/useDisputeQueries.ts` | `GET disputes?status_filter=...` | `getMyDisputes(params)` (extended in `api/disputes.ts` to accept filter params) |

## New files

- `web_portal/src/api/auth.ts` — `loginWidget`, `loginByCode`, `getMe`.
- `web_portal/src/api/documents.ts` — `uploadDocument` (multipart), `getUploadStatus`, `getPassportCompleteness`.
- `web_portal/src/hooks/useActQueries.ts` — `useMyActs`, `useSignAct`, `downloadActPdf`.
- `web_portal/src/hooks/useDocumentQueries.ts` — `usePassportCompleteness`, `useUploadDocument`, `useUploadStatus` (with automatic polling via `refetchInterval`).
- `web_portal/src/lib/types/documents.ts` — `DocumentUploadResponse`, `DocumentStatusResponse`, `PassportCompleteness`, `DocumentValidationFieldDetail`.
- `web_portal/src/lib/types/platform.ts` — `PlatformSettings`, `PlatformSettingsPayload`.

## ESLint guard

`web_portal/eslint.config.js` — added `no-restricted-imports` for
`src/screens/**`, `src/components/**`, `src/hooks/**`:

```js
{
  files: ['src/screens/**/*.{ts,tsx}', 'src/components/**/*.{ts,tsx}', 'src/hooks/**/*.{ts,tsx}'],
  rules: {
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          {
            group: ['@shared/api/client', '@/lib/api'],
            importNames: ['api'],
            message: 'Use functions from src/api/* modules (with hooks in src/hooks/*) instead of calling `api` directly from screens/components.',
          },
        ],
      },
    ],
  },
},
```

Smoke-tested with a temp violation — rule fires with a clear error.

## Incidental fixes pulled in during the refactor

- **`lib/types.ts` `DisputeDetailResponse`** — aligned with backend
  `DisputeResponse` schema (`advertiser_id`, `owner_id` now required;
  added `resolution_comment`, `advertiser_refund_pct`, `owner_payout_pct`,
  `admin_id`, `expires_at`, `updated_at`; removed the phantom embedded
  `placement` subobject that the backend never returns).
- **`lib/types.ts` `UserFeedback`** — renamed `response_text` → `admin_response`
  to match backend contract. `username` changed from optional to
  `string | null`. `status` narrowed to union literal.
- **`screens/shared/DisputeDetail.tsx`** — removed dead references to
  `dispute.placement.channel.username`, `ad_text`, `proposed_price` (those
  fields were never returned by `GET /disputes/{id}` — the display was always
  silently empty). Replaced with `Размещение #{placement_request_id}`.
- **`api/acts.ts` `Act` type** — updated to match backend response dict from
  `acts.py:_act_to_dict` (`act_number`, `act_type`, `act_date`, `sign_method`,
  `pdf_url`, `placement_request_id`, `created_at`). Removed the stale `amount`
  field.
- **`screens/admin/AdminDisputeDetail.tsx`** — updated `statusColor` keys to
  match `DisputeStatus` union (`owner_explained` instead of `owner_reply`;
  added `closed`).

## What did NOT change

- `src/api/*` modules that already exposed the right function (`disputes.ts`,
  `legal.ts`, `acts.ts` partially, `feedback.ts`) got extensions, not
  rewrites.
- Mutation invalidation keys — every hook invalidates the matching query key
  (e.g. `useTopupUserBalance` → `['admin', 'user', userId]` + `['admin', 'users']`).
- No backend change. This is purely a web-portal refactor.

## DoD

- [x] `grep -rn "from.*'@shared/api/client'" web_portal/src/screens/ web_portal/src/components/` → 0.
- [x] `grep -rn "api\.(get|post|put|patch|delete)" web_portal/src/hooks/` → 0.
- [x] ESLint guard rule in place, smoke-tested with a temp violation.
- [x] `npx tsc --noEmit -p tsconfig.app.json` → 0 errors (clean on `web_portal`).
- [x] `npx eslint src/` → no regression vs `main` baseline (1 pre-existing error in `useBillingQueries.ts:44` Date.now, 3 pre-existing warnings; my refactor added and then fixed one `set-state-in-effect` introduction).

Manual UI smoke: deferred — recommended as the first sub-task of the next
session before starting Stage 7, since 14 screens changed and visual
inspection is cheap at this stage.

🔍 Verified against: b914a32 | 📅 Updated: 2026-04-20T00:00:00+03:00
