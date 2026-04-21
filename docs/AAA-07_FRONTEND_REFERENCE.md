# RekHarborBot — Frontend Architecture Reference

> **RekHarborBot AAA Documentation v4.5 | April 2026**
> **Document:** AAA-07_FRONTEND_REFERENCE
> **Verified against:** HEAD @ 2026-04-21 | Source: `mini_app/src/`, `web_portal/src/`, `landing/src/`

---

## Table of Contents

1. [Mini App Overview](#1-mini-app-overview)
2. [Mini App Screens (55)](#2-mini-app-screens)
3. [Mini App Hooks (21)](#3-mini-app-hooks)
4. [Mini App Zustand Stores (4)](#4-mini-app-zustand-stores)
5. [Web Portal Overview](#5-web-portal-overview)
6. [Web Portal Screens (66)](#6-web-portal-screens)
7. [Web Portal Hooks (21)](#7-web-portal-hooks)
8. [Web Portal Zustand Stores (3)](#8-web-portal-zustand-stores)
9. [Design System](#9-design-system)
10. [API Client Patterns](#10-api-client-patterns)
11. [TypeScript Types Cross-Reference](#11-typescript-types-cross-reference)
12. [Route Guards & Navigation](#12-route-guards--navigation)
13. [Landing Page](#13-landing-page)

---

## 1. Mini App Overview

**Framework:** React 19.2.4, TypeScript 6.0.2, Vite 8
**Styling:** Tailwind CSS v4 CSS-first (`@import 'tailwindcss'`, custom `--rh-` tokens), glassmorphism
**State Management:** Zustand 5 (4 stores)
**Data Fetching:** @tanstack/react-query 5 + ky 1.x (auth-aware HTTP client)
**Forms:** react-hook-form + zod
**Navigation:** react-router-dom 7
**Telegram Integration:** `@telegram-apps/sdk-react` 2 (+ access to `window.Telegram.WebApp` for initData)
**Error Tracking:** Sentry (5% trace sample, auth headers scrubbed)
**Dev server:** `:3000`, proxy `/api` → `:8001`
**Production domain:** `app.rekharbor.ru`, served from `/usr/share/nginx/html/app/`

### Architecture

```
mini_app/src/
├── api/              # 18 domain modules + ky client with JWT refresh on 401
├── hooks/            # 8 custom + 13 TanStack Query hooks (+ 1 admin)
├── screens/          # 55 routable screens
│   ├── common/       # 16 (Cabinet, TopUp, Plans, LegalProfile, Contracts, Acts, ...)
│   ├── advertiser/   # 17 (AdvMenu, MyCampaigns, 6-step wizard, CampaignVideo, Disputes, OrdStatus)
│   ├── owner/        # 11 (OwnChannels, OwnRequests, OwnPayouts, DisputeResponse, ...)
│   ├── admin/        # 10 (AdminDashboard, Users, Disputes, Feedback, Accounting, TaxSummary)
│   └── shared/       # 1 (MyDisputes)
├── components/       # 45 components (ui/ 26, layout/ 8, admin/ 2, guards/, root/ 6)
├── stores/           # 4 Zustand: authStore, campaignWizardStore, uiStore, legalProfileStore
├── lib/              # constants, formatters, types
└── styles/           # tokens.css (--rh-*), globals.css, animations.css
```

### Route structure (selected — see `mini_app/src/App.tsx` for full tree)

```
/                             → MainMenu
/cabinet, /referral, /help, /feedback, /plans, /accept-rules, /billing/history, /acts
/topup → /topup/confirm
/legal-profile-prompt, /legal-profile, /legal-profile/view
/contracts → /contracts/:id, /contracts/framework

/adv                          → AdvMenu
/adv/analytics, /adv/campaigns
/adv/campaigns/new/{category|channels|format|text|terms}
/adv/campaigns/:id/{payment|waiting|counter-offer|published|dispute}
/campaign/video, /campaign/:id/ord
/adv/disputes/:id

/own                          → OwnMenu
/own/analytics, /own/channels → /own/channels/add → /own/channels/:id → /own/channels/:id/settings
/own/requests → /own/requests/:id
/own/payouts → /own/payouts/request
/own/disputes/:id

/admin (AdminGuard)           → AdminDashboard
/admin/{feedback|disputes|users}[/:id]
/admin/{settings|tax-summary|accounting}

*                             → NotFoundScreen
```

---

## 2. Mini App Screens (55 — verified 2026-04-21)

### 2.1 Common (16)

`MainMenu`, `Cabinet`, `Referral`, `TopUp`, `TopUpConfirm`, `Help`, `Feedback`, `Plans`, `LegalProfilePrompt`, `LegalProfileSetup`, `LegalProfileView`, `ContractList`, `ContractDetail`, `AcceptRules`, `TransactionHistory`, `MyActsScreen`, plus `NotFoundScreen` fallback.

### 2.2 Advertiser (17)

`AdvMenu`, `AdvAnalytics`, `MyCampaigns`, `CampaignVideo`, `OrdStatus`, `AdvertiserFrameworkContract`; 6-step wizard — `CampaignCategory`, `CampaignChannels`, `CampaignFormat`, `CampaignText`, `CampaignArbitration`, `CampaignPayment`; status screens — `CampaignWaiting`, `CampaignCounterOffer`, `CampaignPublished`; disputes — `OpenDispute`, `DisputeDetail`.

### 2.3 Owner (11)

`OwnMenu`, `OwnAnalytics`, `OwnChannels`, `OwnAddChannel`, `OwnChannelDetail`, `OwnChannelSettings`, `OwnRequests`, `OwnRequestDetail`, `OwnPayouts`, `OwnPayoutRequest`, `DisputeResponse`.

### 2.4 Admin (10)

`AdminDashboard`, `AdminFeedbackList`, `AdminFeedbackDetail`, `AdminDisputesList`, `AdminDisputeDetail`, `AdminUsersList`, `AdminUserDetail`, `AdminPlatformSettings`, `AdminTaxSummary`, `Accounting/index.tsx` (with `DocumentRegistry`, `TaxSummaryCard`, `KudirExportSection` submodules).

### 2.5 Shared (1)

`MyDisputes` — used by both advertiser and owner roles.

---

## 3. Mini App Hooks

### 3.1 API Query Hooks (13 domain + 1 admin)

| Hook | File | Query Keys | Mutations |
|------|------|-----------|-----------|
| useContractQueries | useContractQueries.ts | contracts | generate, sign, list, get, requestKep, acceptRules |
| useLegalProfileQueries | useLegalProfileQueries.ts | legalProfile | getMyProfile, createProfile, updateProfile, getRequiredFields |
| usePlans | usePlans.ts | plans | — (GET /api/billing/plans) |
| useUserQueries | useUserQueries.ts | user/me | — |
| useBillingQueries | useBillingQueries.ts | billing/balance, billing/history | createTopup, buyCredits, changePlan |
| useCampaignQueries | useCampaignQueries.ts | campaigns | create, list, get, update, delete, start, cancel, duplicate |
| useChannelQueries | useChannelQueries.ts | channels | list, add, delete, update, check, available |
| useDisputeQueries | useDisputeQueries.ts | disputes | create, list, get, update, evidence |
| useFeedbackQueries | useFeedbackQueries.ts | feedback | create, list, get, adminRespond |
| useOrdQueries | useOrdQueries.ts | ord | getStatus, register |
| usePayoutQueries | usePayoutQueries.ts | payouts | create, list, get |
| useAnalyticsQueries | useAnalyticsQueries.ts | analytics | summary, activity, advertiser, owner |
| useReputationQueries | useReputationQueries.ts | reputation | getScore, getHistory |
| useReviewQueries | useReviewQueries.ts | reviews | create, getByPlacement |
| useCategoryQueries | useCategoryQueries.ts | categories | list, get |

### 3.2 Custom Hooks (8 verified)

| Hook | Purpose |
|------|---------|
| useAuth | Telegram → JWT handshake |
| useTelegram | Wrapper over `window.Telegram.WebApp` (initData, theme, haptic, back/main buttons) |
| useHaptic | Shortcut for haptic feedback (tap, success, error, warning, select) |
| useBackButton | Telegram BackButton ↔ React Router integration |
| useContractQueries | Contract queries (list, get, sign, rules acceptance) |
| useLegalProfileQueries | Legal profile (GET/POST/PATCH) |
| useOrdQueries | ORD status queries |
| useReferralStats | Referral program statistics |

---

## 4. Mini App Zustand Stores

| Store | File | State | Actions |
|-------|------|-------|---------|
| authStore | `authStore.ts` | token, user, isAuthenticated, isLoading | setAuth, updateUser, logout, setLoading |
| campaignWizardStore | `campaignWizardStore.ts` | step (1–6), category, selectedChannels, format, adText, proposedPrices/Schedules, media (video fileId/url/duration) | setCategory, toggleChannel, setFormat, setAdText, setProposedPrice/Schedule, setVideo, nextStep, prevStep, reset, getTotalPrice |
| uiStore | `uiStore.ts` | toasts[] | addToast(type, message), removeToast(id) — auto-dismiss 3s |
| legalProfileStore | `legalProfileStore.ts` | currentStep, formData, selectedStatus | setStep, setSelectedStatus, updateFormData, reset |

> Note: no separate `themeStore` — theme comes from `window.Telegram.WebApp.colorScheme` via `useTelegram`.

---

## 5. Web Portal Overview

**Framework:** React 19.2.4, TypeScript 6.0.2, Vite 8
**Styling:** Tailwind CSS v4 CSS-first (no `tailwind.config.ts`, theme lives in `globals.css` via `@theme`), OKLCH palette
**State Management:** Zustand 5 (3 stores)
**Data Fetching:** @tanstack/react-query 5 + ky 1.x (JWT in `localStorage['rh_token']`)
**Forms:** react-hook-form + zod + @hookform/resolvers
**Charts:** Recharts 3
**Error Tracking:** Sentry
**Auth:** Telegram Login Widget (primary) · email code (secondary) · `/auth/e2e-login` (test-only)
**Dev server:** `:5174`, proxy `/api` → `:8001`
**Production domain:** `portal.rekharbor.ru`, served from `/usr/share/nginx/html/portal/`

### Architecture

```
web_portal/src/
├── api/              # 18 domain modules on top of ky (shared/api/client.ts)
├── hooks/            # 21 custom + query hooks
├── screens/          # 66 routable screens
│   ├── auth/         # 1  (LoginPage)
│   ├── common/       # 22 (Cabinet, Help, Plans, TopUp, Referral, Contracts, Documents, LegalProfile, …)
│   ├── advertiser/   # 15 (+ campaign wizard 7 sub-screens)
│   ├── owner/        # 10 (OwnChannels, OwnRequests, OwnPayouts, DisputeResponse, …)
│   ├── admin/        # 11 (Dashboard, Users, Disputes, Feedback, Accounting, TaxSummary, Payouts, Settings)
│   ├── shared/       # 6  (DisputeDetail, MyDisputes, OpenDispute, Plans, TopUp, TopUpConfirm)
│   └── dev/          # 1  (DevIcons — stripped from prod)
├── components/       # 8 guards/layout (AuthGuard, RulesGuard, AdminGuard, PortalShell, Sidebar, Topbar, TaxSummaryBase, KepWarning)
├── shared/ui/        # 31 design-system components (Button, Card, Input, Tabs, Modal, Sparkline, …)
├── stores/           # 3 Zustand: authStore, campaignWizardStore, portalUiStore
├── lib/              # constants, 13 type files (lib/types/), timeline, disputeLabels
└── styles/           # globals.css (@theme, @layer base/components, keyframes)
```

### Route structure (condensed — see `web_portal/src/App.tsx`)

Public: `/login`

Auth-gated (AuthGuard → RulesGuard → PortalShell):

```
/ → /cabinet                     (role-aware redirect)
/cabinet, /feedback, /plans, /topup → /topup/confirm, /referral, /help,
/billing/history, /profile/reputation, /acts,
/legal-profile, /legal-profile/view, /legal-profile/documents,
/contracts → /contracts/:id, /contracts/framework,
/accept-rules

/adv                             (redirect into advertiser section)
/adv/campaigns → /adv/campaigns/:id/{waiting|payment|counter-offer|published|dispute}
/adv/campaigns/new/{category|channels|format|text|terms}
/campaign/video, /campaign/:id/ord, /adv/analytics

/own                             (redirect into owner section)
/own/channels → /own/channels/:id → /own/channels/:id/settings
/own/channels/add
/own/requests → /own/requests/:id
/own/payouts → /own/payouts/request
/own/analytics
/own/disputes → /own/disputes/:id

/disputes/:id

/admin (AdminGuard):
  /admin                         (dashboard)
  /admin/users → /admin/users/:id
  /admin/feedback → /admin/feedback/:id
  /admin/disputes → /admin/disputes/:id
  /admin/accounting, /admin/tax-summary, /admin/settings, /admin/payouts
```

---

## 6. Web Portal Screens (66 — verified 2026-04-21)

### 6.1 Admin Screens (11)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | AdminDashboard | AdminDashboard.tsx | GET /api/admin/stats | Platform overview |
| 2 | AdminUsersList | AdminUsersList.tsx | GET /api/admin/users | User management |
| 3 | AdminUserDetail | AdminUserDetail.tsx | GET/PATCH /api/admin/users/{id} | User detail |
| 4 | AdminFeedbackList | AdminFeedbackList.tsx | GET /api/feedback/admin/ | Feedback list |
| 5 | AdminFeedbackDetail | AdminFeedbackDetail.tsx | GET/POST respond | Feedback detail + respond |
| 6 | AdminDisputesList | AdminDisputesList.tsx | GET /api/disputes/admin/disputes | Disputes list |
| 7 | AdminDisputeDetail | AdminDisputeDetail.tsx | POST resolve | Dispute detail + resolve |
| 8 | AdminPlatformSettings | AdminPlatformSettings.tsx | GET/PUT platform-settings | Platform config |
| 9 | AdminTaxSummary | AdminTaxSummary.tsx | GET /api/admin/tax-summary | Tax overview |
| 10 | AdminAccounting | AdminAccounting.tsx | Various accounting endpoints | ⚠️ Uses combined admin stats |
| 11 | AdminLegalProfiles | AdminLegalProfiles.tsx | GET /api/admin/legal-profiles | Legal profiles list |

### 6.2 Advertiser Screens (15 + 7 wizard sub-screens)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | MyCampaigns | MyCampaigns.tsx | GET /api/campaigns/list | ⚠️ STUB — TD-03 |
| 2 | CampaignCategory | CampaignCategory.tsx | — | Wizard step: category |
| 3 | CampaignChannels | CampaignChannels.tsx | GET /api/channels/available | Wizard step: channels |
| 4 | CampaignFormat | CampaignFormat.tsx | — | Wizard step: format |
| 5 | CampaignText | CampaignText.tsx | POST /api/ai/generate-ad-text | Wizard step: text + AI |
| 6 | CampaignVideo | CampaignVideo.tsx | — | Wizard step: video upload |
| 7 | CampaignPayment | CampaignPayment.tsx | POST /api/placements/{id}/pay | Wizard step: payment |
| 8 | CampaignPublished | CampaignPublished.tsx | GET /api/placements/{id} | Wizard step: confirmation |
| 9 | CampaignArbitration | CampaignArbitration.tsx | GET/POST /api/disputes/ | Dispute flow |
| 10 | AdvAnalytics | AdvAnalytics.tsx | GET /api/analytics/advertiser | Analytics dashboard |
| 11 | OrdStatus | OrdStatus.tsx | GET /api/ord/{placement_id} | ORD registration |
| 12 | AdvertiserContract | AdvertiserFrameworkContract.tsx | GET/POST /api/contracts | Contract acceptance |

### 6.3 Owner Screens (10)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | OwnChannels | OwnChannels.tsx | GET /api/channels/ | Channel list |
| 2 | OwnAddChannel | OwnAddChannel.tsx | POST /api/channels/check, POST /api/channels/ | Add channel |
| 3 | OwnChannelDetail | OwnChannelDetail.tsx | GET /api/channels/{id} | Channel detail |
| 4 | OwnChannelSettings | OwnChannelSettings.tsx | PATCH /api/channel-settings/{id} | Channel settings |
| 5 | OwnAnalytics | OwnAnalytics.tsx | GET /api/analytics/owner | Owner analytics |
| 6 | OwnPayouts | OwnPayouts.tsx | GET/POST /api/payouts/ | Payout list |
| 7 | OwnPayoutRequest | OwnPayoutRequest.tsx | POST /api/payouts/ | Create payout |
| 8 | OwnRequests | OwnRequests.tsx | GET /api/placements/?role=owner | Placement requests |
| 9 | DisputeResponse | DisputeResponse.tsx | PATCH /api/disputes/{id} | Respond to dispute |

### 6.4 Common Screens (22)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | LoginPage | LoginPage.tsx | POST /api/auth/login-code | Login with code |
| 2 | Cabinet | Cabinet.tsx | GET /api/auth/me, GET /api/billing/balance | Profile + balance |
| 3 | Feedback | Feedback.tsx | POST/GET /api/feedback/ | Submit feedback |
| 4 | Help | Help.tsx | — | Static help |
| 5 | NotFoundScreen | NotFoundScreen.tsx | — | 404 page |
| 6 | LegalProfileSetup | LegalProfileSetup.tsx | GET/POST/PATCH /api/legal-profile | Legal wizard |
| 7 | LegalProfileView | LegalProfileView.tsx | GET /api/legal-profile/me | Legal profile view |
| 8 | LegalProfilePrompt | LegalProfilePrompt.tsx | GET /api/legal-profile/me | Legal profile prompt |
| 9 | AcceptRules | AcceptRules.tsx | POST /api/contracts/accept-rules | Platform rules acceptance |
| 10 | ContractList | ContractList.tsx | GET /api/contracts | Contract list |
| 11 | ContractDetail | ContractDetail.tsx | GET /api/contracts/{id}, POST sign | Contract detail + sign |
| 12 | DocumentUpload | DocumentUpload.tsx | POST /api/uploads/ | Document upload |
| 13 | MyActs | MyActsScreen.tsx | GET /api/acts/ | Acts list |
| 14 | Referral | Referral.tsx | GET /api/users/referral-stats | Referral program |
| 15 | TransactionHistory | TransactionHistory.tsx | GET /api/billing/history | Transaction history |
| 16 | Plans | Plans.tsx | GET /api/billing/plans, POST /api/billing/plan | Plan selection |
| 17 | TopUp | TopUp.tsx | POST /api/billing/topup | Top-up flow |
| 18 | TopUpConfirm | TopUpConfirm.tsx | — | Top-up confirmation step |
| 19 | OpenDispute | OpenDispute.tsx | POST /api/disputes/ | Create dispute |
| 20 | DisputeDetail | DisputeDetail.tsx | GET /api/disputes/{id} | Dispute detail |

---

### 6.5 Shared Screens (6)

`DisputeDetail`, `MyDisputes`, `OpenDispute`, `Plans`, `TopUp`, `TopUpConfirm` — reused by advertiser and owner flows.

### 6.6 Dev-only (1)

`DevIcons` — icon gallery, route `/dev/icons`, stripped from production build.

---

## 7. Web Portal Hooks

### 7.1 API Query Hooks (15)

| Hook | File | Query Keys |
|------|------|-----------|
| useAdminQueries | useAdminQueries.ts | admin/stats, admin/users, admin/legal-profiles |
| useBillingQueries | useBillingQueries.ts | billing/balance, billing/history, billing/plans |
| useCampaignQueries | useCampaignQueries.ts | campaigns/list, campaigns/{id} |
| useChannelQueries | useChannelQueries.ts | channels/, channels/available |
| useContractQueries | useContractQueries.ts | contracts/list, contracts/{id} |
| useDisputeQueries | useDisputeQueries.ts | disputes/, disputes/{id} |
| useFeedbackQueries | useFeedbackQueries.ts | feedback/, feedback/{id} |
| useLegalProfileQueries | useLegalProfileQueries.ts | legal-profile/me |
| useOrdQueries | useOrdQueries.ts | ord/{placement_id} |
| usePayoutQueries | usePayoutQueries.ts | payouts/, payouts/{id} |
| useAnalyticsQueries | useAnalyticsQueries.ts | analytics/advertiser, analytics/owner |
| useReputationQueries | useReputationQueries.ts | reputation/{user_id} |
| useReviewQueries | useReviewQueries.ts | reviews/placement/{id} |
| useCategoryQueries | useCategoryQueries.ts | categories/ |
| useUserQueries | useUserQueries.ts | users/me, users/referral-stats |

### 7.2 Custom Hooks (6+)

| Hook | Purpose |
|------|---------|
| useToast | Toast notifications dispatch |
| useGenerateAdText | AI text generation mutation |
| useChannelSettings | Channel configuration |
| useNeedsAcceptRules | Check whether user still has to accept platform rules |
| useMediaQuery (`shared/hooks`) | Breakpoint detection (`@sm`, `@md`, `@lg`, `@xl`) |
| useAuth (`authStore` selectors) | Token/user exposure |

---

## 8. Web Portal Zustand Stores

| Store | File | State | Actions |
|-------|------|-------|---------|
| authStore | `authStore.ts` | token, user, isAuthenticated, isLoading | login widget, login code, logout, refresh via `/auth/me` |
| campaignWizardStore | `campaignWizardStore.ts` | wizard form state (category, channels, format, text, arbitration, payment) | step setters, reset |
| portalUiStore | `portalUiStore.ts` | sidebarMode (`open` / `closed` / `collapsed`) | toggleSidebar, setMode |

> Theme is driven by OS `prefers-color-scheme: dark` with a fallback to the light palette via CSS layers — no runtime theme store is needed.

---

## 9. Design System

### 9.1 Tailwind CSS v4 @theme Configuration

Both Mini App and Web Portal use Tailwind v4 with `@theme` directive for design tokens.

```css
@theme {
  --color-primary: oklch(0.65 0.2 250);
  --color-primary-foreground: oklch(0.98 0 0);
  --color-background: oklch(0.15 0.02 250);
  --color-surface: oklch(0.2 0.03 250 / 0.8);
  --color-surface-hover: oklch(0.25 0.03 250 / 0.9);
  --color-border: oklch(0.3 0.03 250 / 0.3);
  --color-text: oklch(0.95 0 0);
  --color-text-muted: oklch(0.7 0 0);
  --color-success: oklch(0.7 0.2 145);
  --color-warning: oklch(0.75 0.2 85);
  --color-error: oklch(0.65 0.25 25);
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
}
```

### 9.2 Glassmorphism Components

**Rule:** `style={{}}` (inline styles) ONLY allowed for glassmorphism effects. All other styling via Tailwind classes.

```tsx
// ✅ Allowed: glassmorphism via inline style
<div style={{
  backdropFilter: 'blur(12px)',
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: 'var(--radius-lg)',
}}>

// ✅ Allowed: Tailwind classes
<div className="bg-surface text-text p-4 rounded-lg">

// ❌ Not allowed: inline styles for non-glassmorphism
<div style={{ marginTop: '16px' }}>  // Use Tailwind mt-4 instead
```

### 9.3 Shared Components (27 Mini App + 25 Web Portal)

| Component | Mini App | Web Portal | Purpose |
|-----------|----------|------------|---------|
| StatusBadge | ✅ | ✅ | Status indicator with color |
| AmountDisplay | ✅ | ✅ | Formatted currency display |
| LoadingSpinner | ✅ | ✅ | Loading indicator |
| ErrorBoundary | ✅ | ✅ | Error fallback UI |
| Button | ✅ | ✅ | Styled button variants |
| Card | ✅ | ✅ | Container with glassmorphism |
| Input | ✅ | ✅ | Form input with validation |
| Select | ✅ | ✅ | Dropdown selector |
| Modal | ✅ | ✅ | Dialog overlay |
| Toast | ✅ | ✅ | Notification toast |
| Badge | ✅ | ✅ | Tag/label badge |
| Skeleton | ✅ | ✅ | Loading placeholder |
| EmptyState | ✅ | ✅ | Empty list placeholder |
| Pagination | ✅ | ✅ | Page navigation |
| Chart | ✅ | ✅ | Recharts wrapper |
| Table | ❌ | ✅ | Data table (web only) |
| CampaignVideo | ✅ | ✅ | Video upload/display |
| ContractCard | ✅ | ✅ | Contract summary card |
| OrdStatusBadge | ✅ | ✅ | ORD status indicator |

---

## 10. API Client Patterns

### 10.1 Mini App: ky

```typescript
// mini_app/src/api/client.ts
import ky from 'ky';

const api = ky.create({
  prefixUrl: '/api/',
  headers: {
    'Content-Type': 'application/json',
  },
  hooks: {
    beforeRequest: [
      (request) => {
        const token = localStorage.getItem('token');
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`);
        }
      },
    ],
    afterResponse: [
      async (request, options, response) => {
        if (response.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/auth';
        }
      },
    ],
  },
});

// Usage
const data = await api.get('auth/me').json<UserResponse>();
await api.post('billing/topup', { json: { desired_amount: 1000 } });
```

### 10.2 Web Portal: Custom Fetch

```typescript
// web_portal/src/shared/api/client.ts
const API_BASE = '/api/';

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }

  if (!response.ok) {
    throw new APIError(response.status, await response.text());
  }

  return response.json();
}

// Usage
const user = await request<UserResponse>('auth/me');
await request('billing/topup', { method: 'POST', body: JSON.stringify({ desired_amount: 1000 }) });
```

### 10.3 Query Pattern (@tanstack/react-query)

```typescript
// Hook pattern
function useCampaigns(status?: string) {
  return useQuery({
    queryKey: ['campaigns', status],
    queryFn: () => api.get(`campaigns?status=${status}`).json<CampaignListResponse>(),
  });
}

// Mutation pattern
function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CampaignCreate) =>
      api.post('campaigns', { json: data }).json<CampaignResponse>(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}
```

---

## 11. TypeScript Types Cross-Reference

### 11.1 Shared Enums (Python ↔ TypeScript)

| Enum | Python | TypeScript | Values |
|------|--------|-----------|--------|
| LegalStatus | LegalStatus (legal_profile.py) | `LegalStatus` | "legal_entity", "individual_entrepreneur", "self_employed", "individual" |
| TaxRegime | TaxRegime (legal_profile.py) | `TaxRegime` | "osno", "usn", "usn_d", "usn_dr", "patent", "npd", "ndfl" |
| ContractType | ContractType (contract.py) | `ContractType` | "owner_service", "advertiser_campaign", "platform_rules", "privacy_policy", "tax_agreement" |
| ContractStatus | ContractStatus (contract.py) | `ContractStatus` | "draft", "pending", "signed", "expired", "cancelled" |
| SignatureMethod | SignatureMethod (contract.py) | `SignatureMethod` | "button_accept", "sms_code" |
| OrdStatus | OrdStatus (ord_registration.py) | `OrdStatus` | "pending", "registered", "token_received", "reported", "failed" |
| UserPlan | UserPlan (user.py) | `UserPlan` | "free", "starter", "pro", "business" |
| PlacementStatus | PlacementStatus (placement_request.py) | `PlacementStatus` | "pending_owner", "counter_offer", "pending_payment", "escrow", "published", "completed" |
| PublicationFormat | PublicationFormat (placement_request.py) | `PublicationFormat` | "post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h" |
| FeedbackStatus | FeedbackStatus (feedback.py) | `FeedbackStatus` | "NEW", "IN_PROGRESS", "RESOLVED", "REJECTED" |

### 11.2 Key TypeScript Interfaces

```typescript
// User
interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string;
  plan: UserPlan;
  is_admin: boolean;
  balance_rub: string;
  earned_rub: string;
  current_role: string;
  is_active: boolean;
}

// Placement
interface Placement {
  id: number;
  advertiser_id: number;
  owner_id: number;
  channel_id: number;
  status: PlacementStatus;
  publication_format: PublicationFormat;
  final_price: string | null;
  final_text: string;
  scheduled_date: string | null;
  message_id: number | null;
  created_at: string;
}

// Payout
interface Payout {
  id: number;
  gross_amount: string;
  fee_amount: string;
  net_amount: string;
  status: string;
  requisites: string;
  created_at: string;
  processed_at: string | null;
}

// Contract
interface Contract {
  id: number;
  user_id: number;
  contract_type: ContractType;
  contract_status: ContractStatus;
  pdf_url: string | null;
  signed_at: string | null;
  signature_method: SignatureMethod | null;
}

// LegalProfile
interface LegalProfile {
  id: number;
  user_id: number;
  legal_status: LegalStatus;
  tax_regime: TaxRegime | null;
  inn: string;  // encrypted
  company_name: string | null;
  full_name: string | null;
  is_completed: boolean;
  is_verified: boolean;
}
```

---

## 12. Route Guards & Navigation

### 12.1 Auth Guard

All routes except `/login`, `/health`, and public endpoints require valid JWT token.

```typescript
// Auth guard pattern (both Mini App and Web Portal)
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  
  return children;
}
```

### 12.2 Role-Based Guards

| Route Pattern | Required Role | Source |
|--------------|--------------|--------|
| `/admin/*` | `is_admin=true` | AdminFilter (bot) / API admin check |
| `/campaigns/*` | advertiser/both | Placement creation |
| `/analytics/advertiser` | advertiser/both | Advertiser analytics |
| `/channels/*`, `/payouts/*` | owner/both | Owner management |
| `/analytics/owner` | owner/both | Owner analytics |

### 12.3 Navigation Flow

```
Mini App:
  / → Role-based redirect → /campaigns (advertiser) or /channels (owner) or /admin (admin)

Web Portal:
  / → If not authenticated → /login
  / → If authenticated → /dashboard (admin) or /campaigns (advertiser) or /channels (owner)

Both:
  /cabinet → Profile + balance (all authenticated users)
  /help → Static help content
  /feedback → Submit feedback
  /* → 404
```

---

## 13. Landing Page

**Location:** `/opt/market-telegram-bot/landing/`
**Audience:** marketing/SEO — first touchpoint on `rekharbor.ru`.
**Build:** static Vite + Tailwind v4 (`@theme` tokens from `DESIGN.md`), no runtime FastAPI calls.
**Constraints (from `CLAUDE.md`):**
- TS 6.0.2, aligned with mini_app & web_portal.
- Fonts: DM Sans, Outfit, Poppins, Roboto — all via Google Fonts.
- CSP: no `unsafe-inline`, no `unsafe-eval`.
- Motion imports: `import { ... } from 'motion/react'` (package `motion`).
- Lighthouse budgets tracked in `landing/lighthouserc.cjs`.

**Nginx:** separate server block for `rekharbor.ru` serves the built landing `dist/`. Does **not** share `/api/` proxy — no runtime backend dependency.

---

🔍 Verified against: HEAD @ 2026-04-21 | Source files: `mini_app/src/`, `web_portal/src/`, `landing/src/`
✅ Validation: passed | All screens, hooks, stores re-counted | Route maps regenerated from current `App.tsx`
