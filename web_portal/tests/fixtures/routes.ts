// Protected routes for the route-sweep smoke test.
// Source of truth: web_portal/src/App.tsx router config.
// Role comment = which seeded role reaches the route without a 403/redirect.

import type { Role } from './roles'

export interface RouteSpec {
  /** URL path (prefixed with /) */
  path: string
  /** Which seeded role to run this route under */
  role: Role
  /** Skip individual assertions if known to fail for unrelated reasons */
  skip?: {
    noBreadcrumbs?: boolean
    allowOverflow?: boolean
  }
}

// ── Common routes (any authenticated user) ──
const common: RouteSpec[] = [
  { path: '/cabinet', role: 'advertiser' },
  { path: '/feedback', role: 'advertiser' },
  { path: '/plans', role: 'advertiser' },
  { path: '/topup', role: 'advertiser' },
  { path: '/referral', role: 'advertiser' },
  { path: '/help', role: 'advertiser' },
  { path: '/billing/history', role: 'advertiser' },
  { path: '/profile/reputation', role: 'advertiser' },
  { path: '/acts', role: 'advertiser' },
  { path: '/legal-profile/view', role: 'advertiser' },
  { path: '/contracts', role: 'advertiser' },
]

// ── Advertiser routes ──
const advertiser: RouteSpec[] = [
  { path: '/adv/campaigns', role: 'advertiser' },
  { path: '/adv/campaigns/new/category', role: 'advertiser' },
  { path: '/adv/campaigns/new/channels', role: 'advertiser' },
  { path: '/adv/campaigns/new/format', role: 'advertiser' },
  { path: '/adv/campaigns/new/text', role: 'advertiser' },
  { path: '/adv/campaigns/new/terms', role: 'advertiser' },
  { path: '/adv/disputes', role: 'advertiser' },
  { path: '/adv/analytics', role: 'advertiser' },
  { path: '/contracts/framework', role: 'advertiser' },
]

// ── Owner routes ──
const owner: RouteSpec[] = [
  { path: '/own/analytics', role: 'owner' },
  { path: '/own/channels', role: 'owner' },
  { path: '/own/channels/add', role: 'owner' },
  { path: '/own/requests', role: 'owner' },
  { path: '/own/disputes', role: 'owner' },
  { path: '/own/payouts', role: 'owner' },
  { path: '/own/payouts/request', role: 'owner' },
]

// ── Admin routes ──
const admin: RouteSpec[] = [
  { path: '/admin', role: 'admin' },
  { path: '/admin/users', role: 'admin' },
  { path: '/admin/feedback', role: 'admin' },
  { path: '/admin/disputes', role: 'admin' },
  { path: '/admin/payouts', role: 'admin' },
  { path: '/admin/accounting', role: 'admin' },
  { path: '/admin/tax-summary', role: 'admin' },
  { path: '/admin/settings', role: 'admin' },
]

export const ROUTES: RouteSpec[] = [...common, ...advertiser, ...owner, ...admin]
