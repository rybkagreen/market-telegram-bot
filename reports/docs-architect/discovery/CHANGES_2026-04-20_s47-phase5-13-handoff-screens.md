# CHANGES 2026-04-20 — S-47 Phase 5: 13 DS v2 handoff screens

## Affected files

### New primitives (Phase 5.0)
- `web_portal/src/shared/ui/ScreenHeader.tsx` — new
- `web_portal/src/shared/ui/LinkButton.tsx` — new
- `web_portal/src/shared/ui/Button.tsx` — added `iconLeft` / `iconRight: IconName` props
- `web_portal/src/shared/ui/StepIndicator.tsx` — rewritten (numbered pills + inline labels; labels-per-step)
- `web_portal/src/shared/ui/index.ts` — export ScreenHeader, LinkButton

### 13 handoff screens ported (pixel-perfect per `reports/design/test-avatars-handoff-2026-04-20/project/*.html`)
- `web_portal/src/screens/shared/Plans.tsx`
- `web_portal/src/screens/shared/TopUp.tsx`
- `web_portal/src/screens/shared/TopUpConfirm.tsx`
- `web_portal/src/screens/common/TransactionHistory.tsx`
- `web_portal/src/screens/common/ReputationHistory.tsx`
- `web_portal/src/screens/common/MyActsScreen.tsx`
- `web_portal/src/screens/common/Referral.tsx`
- `web_portal/src/screens/common/Help.tsx`
- `web_portal/src/screens/common/Feedback.tsx`
- `web_portal/src/screens/common/LegalProfileSetup.tsx`
- `web_portal/src/screens/common/ContractList.tsx`
- `web_portal/src/screens/common/DocumentUpload.tsx`
- `web_portal/src/screens/common/AcceptRules.tsx`

### Legacy StepIndicator callers updated (labels-per-step format)
- `web_portal/src/screens/advertiser/CampaignVideo.tsx`
- `web_portal/src/screens/advertiser/campaign/CampaignCategory.tsx`
- `web_portal/src/screens/advertiser/campaign/CampaignChannels.tsx`
- `web_portal/src/screens/advertiser/campaign/CampaignFormat.tsx`
- `web_portal/src/screens/advertiser/campaign/CampaignText.tsx`
- `web_portal/src/screens/advertiser/campaign/CampaignArbitration.tsx`

## Business logic impact

### Preserved unchanged
- Data-layer hooks (useMe, useBalance, useMyCampaigns, useTransactionHistory,
  useReputationHistory, useMyActs, useSignAct, useReferralStats, useCreateFeedback,
  useMyLegalProfile / useCreateLegalProfile / useUpdateLegalProfile /
  useValidateInn / useRequiredFields / useValidateEntity, useContracts /
  usePlatformRules / useAcceptRules, useUploadDocument / usePassportCompleteness /
  useUploadStatus, useInitiateTopup / useTopupStatus).
- FNS validation mutation flow in LegalProfileSetup (including passport series/
  number length checks for individual / self-employed).
- DocumentUpload OCR + passport-completeness + quality-score + validation-details
  logic preserved (presentation wrapped in DS v2 hero + progress ring + sidebar).
- AcceptRules scroll-to-bottom gate + 3-checkbox agreement + navigation side
  effects (`qc.invalidateQueries(['user', 'me'])` → `navigate('/cabinet')`).
- ContractList `usePlatformRules` viewer modal with DOMPurify HTML sanitization.
- TopUpConfirm polling state mapping `useTopupStatus` `{ apiStatus, timedOut }` →
  live enum `pending | succeeded | canceled | timeout`.

### Additive only
- `Button.iconLeft` / `iconRight: IconName` are new optional props, existing
  callers unaffected. Icon sizes auto-pick from size: sm=14, md=16, lg=18.
- `LinkButton` is a new inline text-link primitive.

### Semantic change
- `StepIndicator.labels[i]` now means "label for step i+1" (0-indexed).
  Previously: `labels[current]` (1-indexed with a leading filler slot).
  All 7 existing callers migrated to pass full N-label arrays.

## New / changed API / FSM / DB contracts

- **None.** Phase 5 is pure frontend; no backend endpoints, routers,
  services, models, migrations, or Celery tasks touched.

## Verification

- `npx tsc --noEmit -p web_portal/tsconfig.app.json` → **exit 0**
- `docker compose up -d --build nginx api` → **nginx healthy, api healthy**
  (rebuilds the mini_app / web_portal bundle inside the nginx Dockerfile
   and recreates containers, per the `MEMORY.md` Applying-Changes rule)
- All 9 docker services running (postgres, redis, nginx, api, bot,
  celery_beat, flower, worker_background, worker_critical)

## Deferred to follow-up sessions

- **Phase 6** — ~25 design-from-tokens screens (advertiser wizard,
  owner, admin — see plan §7.17).
- **Phase 7** — role switcher, density toggle, a11y audit, perf-check.
- **Phase 8** — `lucide-react` → `<Icon>` migration lock (ESLint
  error-level).
- Live TopUpConfirm "elapsed seconds" counter is reset on hot-reload —
  acceptable for now since real pending state is driven by server-side
  polling, but consider persisting `startedAt` in session storage.
- Feedback form prepends topic/priority context to the free-text `text`
  body (`[Тема · Приоритет]\n\n<text>`); consider extending the
  `UserFeedback` API with explicit `topic` / `priority` fields in a
  future sprint.

🔍 Verified against: ecc43f3 | 📅 Updated: 2026-04-20T00:00:00+03:00
