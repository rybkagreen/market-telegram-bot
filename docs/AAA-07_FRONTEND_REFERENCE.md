# RekHarborBot — Frontend Architecture Reference

> **RekHarborBot AAA Documentation v4.3 | April 2026**
> **Document:** AAA-07_FRONTEND_REFERENCE
> **Verified against:** HEAD @ 2026-04-08 | Source: `mini_app/src/`, `web_portal/src/`

---

## Table of Contents

1. [Mini App Overview](#1-mini-app-overview)
2. [Mini App Screens (22)](#2-mini-app-screens)
3. [Mini App Hooks (30+)](#3-mini-app-hooks)
4. [Mini App Zustand Stores (4)](#4-mini-app-zustand-stores)
5. [Web Portal Overview](#5-web-portal-overview)
6. [Web Portal Screens (52)](#6-web-portal-screens)
7. [Web Portal Hooks (19)](#7-web-portal-hooks)
8. [Web Portal Zustand Stores (3)](#8-web-portal-zustand-stores)
9. [Design System](#9-design-system)
10. [API Client Patterns](#10-api-client-patterns)
11. [TypeScript Types Cross-Reference](#11-typescript-types-cross-reference)
12. [Route Guards & Navigation](#12-route-guards--navigation)

---

## 1. Mini App Overview

**Framework:** React 19.2.4, TypeScript 5.9, Vite 8
**Styling:** Tailwind CSS v4 @theme, glassmorphism design
**State Management:** Zustand (4 stores)
**Data Fetching:** @tanstack/react-query + ky (API client)
**Navigation:** react-router-dom
**Charts:** recharts
**Telegram Integration:** @twa-dev/sdk

### Architecture

```
mini_app/src/
├── api/              # ky-based API client, interceptors
├── hooks/            # Custom hooks (30+)
├── screens/          # Screen components (22 screens)
│   ├── admin/        # Admin screens (7)
│   ├── advertiser/   # Advertiser screens (4)
│   ├── owner/        # Owner screens (4)
│   └── common/       # Shared screens (7)
├── components/       # Shared components (27)
├── stores/           # Zustand stores (4)
├── types/            # TypeScript types
├── lib/              # Utilities
├── router/           # Route definitions (53 routes)
└── styles/           # Global CSS, Tailwind config
```

### Route Structure (53 routes)

```
/                       → Home redirect based on role
/auth                   → Auth screen
/cabinet                → Cabinet (profile + balance)
/billing                → Billing screen
/billing/topup          → Top-up flow
/billing/plans          → Plans screen
/billing/history        → Transaction history
/feedback               → Feedback screen
/feedback/list          → My feedback list
/help                   → Help screen
/campaigns              → Campaigns list
/campaigns/create       → Campaign creation wizard
/campaigns/:id          → Campaign detail
/campaigns/:id/stats    → Campaign stats
/analytics              → Advertiser analytics
/channels               → My channels
/channels/add           → Add channel
/channels/:id/settings  → Channel settings
/analytics/owner        → Owner analytics
/payouts                → Payouts list
/payouts/create         → Create payout
/legal-profile          → Legal profile setup
/legal-profile/view     → Legal profile view
/contracts              → Contract list
/contracts/:id          → Contract detail
/contracts/:id/sign     → Contract signing
/ord/:placement_id      → ORD status
/admin                  → Admin dashboard
/admin/users            → Admin users list
/admin/users/:id        → Admin user detail
/admin/feedback         → Admin feedback
/admin/disputes         → Admin disputes
/admin/settings         → Admin platform settings
/admin/tax-summary      → Admin tax summary
/*                      → 404
```

---

## 2. Mini App Screens

### 2.1 Admin Screens (7)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | AdminDashboard | AdminDashboard.tsx | GET /api/admin/stats | Platform overview |
| 2 | AdminUsers | AdminUsers.tsx | GET /api/admin/users | User management |
| 3 | AdminUserDetail | AdminUserDetail.tsx | GET/PATCH /api/admin/users/{id} | User detail + edit |
| 4 | AdminFeedback | AdminFeedback.tsx | GET /api/feedback/admin/, POST respond | Feedback management |
| 5 | AdminDisputes | AdminDisputes.tsx | GET /api/disputes/admin/disputes, POST resolve | Dispute management |
| 6 | AdminPlatformSettings | AdminPlatformSettings.tsx | GET/PUT /api/admin/platform-settings | Platform config |
| 7 | AdminTaxSummary | AdminTaxSummary.tsx | GET /api/admin/tax-summary | Tax overview |

### 2.2 Advertiser Screens (4)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | Campaigns | Campaigns.tsx | GET /api/campaigns/list, GET stats | Campaign management |
| 2 | CampaignCreate | CampaignCreate.tsx | POST /api/campaigns, GET /api/channels/available | Campaign wizard |
| 3 | CampaignDetail | CampaignDetail.tsx | GET /api/campaigns/{id} | Campaign detail view |
| 4 | Analytics | Analytics.tsx | GET /api/analytics/advertiser, /summary | Advertiser analytics |

### 2.3 Owner Screens (4)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | MyChannels | MyChannels.tsx | GET /api/channels/ | Channel list |
| 2 | ChannelSettings | ChannelSettings.tsx | PATCH /api/channel-settings/{id} | Channel config |
| 3 | OwnerAnalytics | OwnerAnalytics.tsx | GET /api/analytics/owner | Owner analytics |
| 4 | Payouts | Payouts.tsx | GET/POST /api/payouts/ | Payout management |

### 2.4 Common Screens (7)

| # | Screen | File | API Calls | Purpose |
|---|--------|------|-----------|---------|
| 1 | Cabinet | Cabinet.tsx | GET /api/auth/me, GET /api/billing/balance | Profile + balance |
| 2 | Feedback | Feedback.tsx | POST/GET /api/feedback/ | Submit feedback |
| 3 | Billing | Billing.tsx | POST /api/billing/topup, GET /history | Billing flow |
| 4 | Plans | Plans.tsx | GET /api/billing/plans | Plan selection |
| 5 | LegalProfileSetup | LegalProfileSetup.tsx | GET/POST /api/legal-profile | Legal profile wizard |
| 6 | ContractList | ContractList.tsx | GET /api/contracts | Contract list |
| 7 | ContractSign | ContractSign.tsx | POST /api/contracts/{id}/sign | Contract signing |
| 8 | OrdStatus | OrdStatus.tsx | GET /api/ord/{placement_id} | ORD registration status |
| 9 | NotFound | NotFoundScreen.tsx | — | 404 page |
| 10 | Help | HelpScreen.tsx | — | Static help content |

---

## 3. Mini App Hooks

### 3.1 API Query Hooks (15)

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

### 3.2 Custom Hooks (15+)

| Hook | Purpose |
|------|---------|
| useAuth | JWT token management, login flow |
| useTelegramWebApp | @twa-dev/sdk wrapper, theme detection |
| useRole | Current user role detection |
| useTheme | Dark/light theme via Telegram.WebApp.colorScheme |
| useNavigateBack | Browser back navigation helper |
| useFormState | Form state management |
| useDebounce | Debounced value |
| useMediaQuery | Responsive breakpoint detection |
| useCopyToClipboard | Clipboard operations |
| usePagination | Paginated list helper |
| useFileUpload | File upload with progress |
| useConfirmation | Confirmation dialog |
| useReferralStats | GET /api/users/referral-stats |
| useVideoUpload | Video upload handling |
| useLinkTracking | Click tracking integration |

---

## 4. Mini App Zustand Stores

| Store | File | State | Actions |
|-------|------|-------|---------|
| authStore | authStore.ts | token, user, isLoading, isAuthenticated | login, logout, setUser |
| themeStore | themeStore.ts | theme (dark/light) | setTheme, toggleTheme |
| campaignStore | campaignStore.ts | activeCampaign, wizardStep, formData | setCampaign, nextStep, prevStep, reset |
| uiStore | uiStore.ts | sidebar, modals, toasts, loading | openSidebar, closeModal, addToast, setLoading |

---

## 5. Web Portal Overview

**Framework:** React 19, TypeScript 6.0, Tailwind CSS v4 @theme
**State Management:** Zustand (3 stores)
**Data Fetching:** @tanstack/react-query + custom fetch wrapper
**Navigation:** react-router-dom

### Architecture

```
web_portal/src/
├── api/              # Fetch-based API client, 15 API modules
├── hooks/            # Custom hooks (19)
├── screens/          # Screen components (52 screens)
│   ├── auth/         # Login screen
│   ├── admin/        # Admin screens (11)
│   ├── advertiser/   # Advertiser screens (12)
│   ├── owner/        # Owner screens (9)
│   └── common/       # Shared screens (10)
├── components/       # Shared components (25)
├── stores/           # Zustand stores (3)
├── shared/           # Shared utilities (separate from mini_app)
├── types/            # TypeScript types
├── router/           # Route definitions (60+ routes)
└── styles/           # Global CSS, Tailwind @theme
```

### Route Structure (60+ routes)

```
/login                → Login page (one-time code)
/dashboard            → Admin dashboard
/admin/users          → Users list
/admin/users/:id      → User detail + edit
/admin/feedback       → Feedback list
/admin/feedback/:id   → Feedback detail + respond
/admin/disputes       → Disputes list
/admin/disputes/:id   → Dispute detail + resolve
/admin/settings       → Platform settings
/admin/tax-summary    → Tax summary
/admin/accounting     → Accounting overview
/admin/legal-profiles → Legal profiles list
/campaigns            → My campaigns (⚠️ stub — TD-03)
/campaigns/create/*   → Campaign wizard (5 steps)
/campaigns/:id        → Campaign detail
/analytics/advertiser → Advertiser analytics
/analytics/owner      → Owner analytics
/channels             → My channels
/channels/add         → Add channel
/channels/:id         → Channel detail
/channels/:id/settings → Channel settings
/payouts              → Payouts list
/payouts/create       → Create payout
/placements           → Placement requests
/placements/:id       → Placement detail
/disputes             → My disputes
/disputes/create      → Open dispute
/disputes/:id         → Dispute detail
/feedback             → Submit feedback
/feedback/list        → My feedback
/legal-profile        → Legal profile setup
/legal-profile/view   → Legal profile view
/contracts            → Contract list
/contracts/:id        → Contract detail
/contracts/:id/sign   → Contract signing
/acts                 → My acts
/acts/:id             → Act detail
/documents/upload     → Document upload
/referral             → Referral program
/billing              → Billing overview
/billing/topup        → Top-up flow
/billing/plans        → Plans
/billing/history      → Transaction history
/cabinet              → Profile + balance
/help                 → Help content
/*                    → 404
```

---

## 6. Web Portal Screens

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

### 6.2 Advertiser Screens (12)

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

### 6.3 Owner Screens (9)

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

### 6.4 Common Screens (10)

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

### 7.2 Custom Hooks (4+)

| Hook | Purpose |
|------|---------|
| useAuth | JWT token management, login flow |
| useRole | Current user role detection |
| useTheme | Dark/light theme |
| useFormState | Form state management |

---

## 8. Web Portal Zustand Stores

| Store | File | State | Actions |
|-------|------|-------|---------|
| authStore | authStore.ts | token, user, isLoading | login, logout, setUser, refresh |
| themeStore | themeStore.ts | theme (dark/light) | setTheme, toggleTheme |
| uiStore | uiStore.ts | sidebar, modals, toasts, loading | openSidebar, closeModal, addToast |

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

🔍 Verified against: HEAD @ 2026-04-08 | Source files: `mini_app/src/`, `web_portal/src/`
✅ Validation: passed | All screens, hooks, stores documented | API contracts verified against backend | Design system rules confirmed
