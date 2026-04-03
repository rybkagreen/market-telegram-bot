import { lazy } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Outlet, createBrowserRouter, RouterProvider } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { RulesGuard } from '@/components/RulesGuard'

// ═══ Common ═══
const MainMenu           = lazy(() => import('@/screens/common/MainMenu'))
const RoleSelect         = lazy(() => import('@/screens/common/RoleSelect'))
const Cabinet            = lazy(() => import('@/screens/common/Cabinet'))
const Referral           = lazy(() => import('@/screens/common/Referral'))
const TopUp              = lazy(() => import('@/screens/common/TopUp'))
const TopUpConfirm       = lazy(() => import('@/screens/common/TopUpConfirm'))
const Help               = lazy(() => import('@/screens/common/Help'))
const Feedback           = lazy(() => import('@/screens/common/Feedback'))  // ДОБАВЛЕНО (2026-03-18)
const Plans              = lazy(() => import('@/screens/common/Plans'))
const LegalProfilePrompt = lazy(() => import('@/screens/common/LegalProfilePrompt'))
const LegalProfileSetup  = lazy(() => import('@/screens/common/LegalProfileSetup'))
const LegalProfileView   = lazy(() => import('@/screens/common/LegalProfileView'))
const ContractList       = lazy(() => import('@/screens/common/ContractList'))
const ContractDetail     = lazy(() => import('@/screens/common/ContractDetail'))
const AcceptRules        = lazy(() => import('@/screens/common/AcceptRules'))
const TransactionHistory = lazy(() => import('@/screens/common/TransactionHistory'))

// ═══ Advertiser ═══
const AdvMenu        = lazy(() => import('@/screens/advertiser/AdvMenu'))
const AdvAnalytics   = lazy(() => import('@/screens/advertiser/AdvAnalytics'))
const MyCampaigns    = lazy(() => import('@/screens/advertiser/MyCampaigns'))

// ═══ Advertiser / S5 additions ═══
const CampaignVideo              = lazy(() => import('@/screens/advertiser/CampaignVideo'))
const OrdStatus                  = lazy(() => import('@/screens/advertiser/OrdStatus'))
const AdvertiserFrameworkContract = lazy(() => import('@/screens/advertiser/AdvertiserFrameworkContract'))

// ═══ Advertiser / Campaign wizard ═══
const CampaignCategory   = lazy(() => import('@/screens/advertiser/campaign/CampaignCategory'))
const CampaignChannels   = lazy(() => import('@/screens/advertiser/campaign/CampaignChannels'))
const CampaignFormat     = lazy(() => import('@/screens/advertiser/campaign/CampaignFormat'))
const CampaignText       = lazy(() => import('@/screens/advertiser/campaign/CampaignText'))
const CampaignArbitration = lazy(() => import('@/screens/advertiser/campaign/CampaignArbitration'))
const CampaignWaiting    = lazy(() => import('@/screens/advertiser/campaign/CampaignWaiting'))
const CampaignPayment    = lazy(() => import('@/screens/advertiser/campaign/CampaignPayment'))
const CampaignPublished  = lazy(() => import('@/screens/advertiser/campaign/CampaignPublished'))

// ═══ Advertiser / Disputes ═══
const OpenDispute    = lazy(() => import('@/screens/advertiser/disputes/OpenDispute'))
const DisputeDetail  = lazy(() => import('@/screens/advertiser/disputes/DisputeDetail'))

// ═══ Owner ═══
const OwnMenu            = lazy(() => import('@/screens/owner/OwnMenu'))
const OwnAnalytics       = lazy(() => import('@/screens/owner/OwnAnalytics'))
const OwnChannels        = lazy(() => import('@/screens/owner/OwnChannels'))
const OwnAddChannel      = lazy(() => import('@/screens/owner/OwnAddChannel'))
const OwnChannelDetail   = lazy(() => import('@/screens/owner/OwnChannelDetail'))
const OwnChannelSettings = lazy(() => import('@/screens/owner/OwnChannelSettings'))
const OwnRequests        = lazy(() => import('@/screens/owner/OwnRequests'))
const OwnRequestDetail   = lazy(() => import('@/screens/owner/OwnRequestDetail'))
const OwnPayouts         = lazy(() => import('@/screens/owner/OwnPayouts'))
const OwnPayoutRequest   = lazy(() => import('@/screens/owner/OwnPayoutRequest'))
const DisputeResponse    = lazy(() => import('@/screens/owner/DisputeResponse'))

// ═══ Admin ═══ (PHASE-5)
const AdminDashboard          = lazy(() => import('@/screens/admin/AdminDashboard'))
const AdminFeedbackList       = lazy(() => import('@/screens/admin/AdminFeedbackList'))
const AdminFeedbackDetail     = lazy(() => import('@/screens/admin/AdminFeedbackDetail'))
const AdminDisputesList       = lazy(() => import('@/screens/admin/AdminDisputesList'))
const AdminDisputeDetail      = lazy(() => import('@/screens/admin/AdminDisputeDetail'))
const AdminUsersList          = lazy(() => import('@/screens/admin/AdminUsersList'))
const AdminUserDetail         = lazy(() => import('@/screens/admin/AdminUserDetail'))
const AdminPlatformSettings   = lazy(() => import('@/screens/admin/AdminPlatformSettings'))

function RulesGuardLayout() {
  return (
    <RulesGuard>
      <Outlet />
    </RulesGuard>
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      {
        element: <RulesGuardLayout />,
        children: [
      // ── Common ──
      { index: true,                      element: <MainMenu /> },
      { path: 'role',                     element: <RoleSelect /> },
      { path: 'cabinet',                  element: <Cabinet /> },
      { path: 'referral',                 element: <Referral /> },
      { path: 'topup',                    element: <TopUp /> },
      { path: 'topup/confirm',            element: <TopUpConfirm /> },
      { path: 'help',                     element: <Help /> },
      { path: 'feedback',                 element: <Feedback /> },  // ДОБАВЛЕНО (2026-03-18)
      { path: 'plans',                    element: <Plans /> },
      { path: 'legal-profile-prompt',     element: <LegalProfilePrompt /> },
      { path: 'legal-profile',            element: <LegalProfileSetup /> },
      { path: 'legal-profile/view',       element: <LegalProfileView /> },
      { path: 'contracts',                element: <ContractList /> },
      { path: 'contracts/:id',            element: <ContractDetail /> },
      { path: 'accept-rules',             element: <AcceptRules /> },
      { path: 'billing/history',          element: <TransactionHistory /> },
      { path: 'campaign/video',           element: <CampaignVideo /> },
      { path: 'campaign/:id/ord',         element: <OrdStatus /> },
      { path: 'contracts/framework',      element: <AdvertiserFrameworkContract /> },

      // ── Advertiser ──
      { path: 'adv',                                    element: <AdvMenu /> },
      { path: 'adv/analytics',                          element: <AdvAnalytics /> },
      { path: 'adv/campaigns',                          element: <MyCampaigns /> },
      { path: 'adv/campaigns/new/category',             element: <CampaignCategory /> },
      { path: 'adv/campaigns/new/channels',             element: <CampaignChannels /> },
      { path: 'adv/campaigns/new/format',               element: <CampaignFormat /> },
      { path: 'adv/campaigns/new/text',                 element: <CampaignText /> },
      { path: 'adv/campaigns/new/terms',                element: <CampaignArbitration /> },
      { path: 'adv/campaigns/:id/waiting',              element: <CampaignWaiting /> },
      { path: 'adv/campaigns/:id/payment',              element: <CampaignPayment /> },
      { path: 'adv/campaigns/:id/published',            element: <CampaignPublished /> },
      { path: 'adv/campaigns/:id/dispute',              element: <OpenDispute /> },
      { path: 'adv/disputes/:id',                       element: <DisputeDetail /> },

      // ── Owner ──
      { path: 'own',                                    element: <OwnMenu /> },
      { path: 'own/analytics',                          element: <OwnAnalytics /> },
      { path: 'own/channels',                           element: <OwnChannels /> },
      { path: 'own/channels/add',                       element: <OwnAddChannel /> },
      { path: 'own/channels/:id',                       element: <OwnChannelDetail /> },
      { path: 'own/channels/:id/settings',              element: <OwnChannelSettings /> },
      { path: 'own/requests',                           element: <OwnRequests /> },
      { path: 'own/requests/:id',                       element: <OwnRequestDetail /> },
      { path: 'own/payouts',                            element: <OwnPayouts /> },
      { path: 'own/payouts/request',                    element: <OwnPayoutRequest /> },
      { path: 'own/disputes/:id',                       element: <DisputeResponse /> },

      // ── Admin ── (PHASE-5)
      { path: 'admin',                                  element: <AdminDashboard /> },
      { path: 'admin/feedback',                         element: <AdminFeedbackList /> },
      { path: 'admin/feedback/:id',                     element: <AdminFeedbackDetail /> },
      { path: 'admin/disputes',                         element: <AdminDisputesList /> },
      { path: 'admin/disputes/:id',                     element: <AdminDisputeDetail /> },
      { path: 'admin/users',                            element: <AdminUsersList /> },
      { path: 'admin/users/:id',                        element: <AdminUserDetail /> },
      { path: 'admin/settings',                         element: <AdminPlatformSettings /> },
        ],
      },
    ],
  },
])

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
