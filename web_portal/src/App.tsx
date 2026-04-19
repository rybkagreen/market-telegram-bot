import { lazy } from 'react'
import { Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { PortalShell } from '@/components/layout/PortalShell'
import { AuthGuard } from '@/components/guards/AuthGuard'
import { RulesGuard } from '@/components/guards/RulesGuard'
import AdminGuard from '@/components/guards/AdminGuard'

// ═══ Auth ═══
const LoginPage = lazy(() => import('@/screens/auth/LoginPage'))

// ═══ Common screens ═══
const Cabinet = lazy(() => import('@/screens/common/Cabinet'))
const Feedback = lazy(() => import('@/screens/common/Feedback'))
const NotFoundScreen = lazy(() => import('@/screens/common/NotFoundScreen'))
const Plans = lazy(() => import('@/screens/shared/Plans'))
const TopUp = lazy(() => import('@/screens/shared/TopUp'))
const TopUpConfirm = lazy(() => import('@/screens/shared/TopUpConfirm'))
const Referral = lazy(() => import('@/screens/common/Referral'))
const Help = lazy(() => import('@/screens/common/Help'))
const TransactionHistory = lazy(() => import('@/screens/common/TransactionHistory'))
const AcceptRules = lazy(() => import('@/screens/common/AcceptRules'))
const MyActsScreen = lazy(() => import('@/screens/common/MyActsScreen'))
const LegalProfilePrompt = lazy(() => import('@/screens/common/LegalProfilePrompt'))
const LegalProfileSetup = lazy(() => import('@/screens/common/LegalProfileSetup'))
const LegalProfileView = lazy(() => import('@/screens/common/LegalProfileView'))
const ContractList = lazy(() => import('@/screens/common/ContractList'))
const ContractDetail = lazy(() => import('@/screens/common/ContractDetail'))
const DocumentUpload = lazy(() => import('@/screens/common/DocumentUpload'))
const ReputationHistory = lazy(() => import('@/screens/common/ReputationHistory'))

// ═══ Advertiser screens ═══
const AdvAnalytics = lazy(() => import('@/screens/advertiser/AdvAnalytics'))
const CampaignPayment = lazy(() => import('@/screens/advertiser/CampaignPayment'))
const CampaignCounterOffer = lazy(() => import('@/screens/advertiser/CampaignCounterOffer'))
const MyCampaigns = lazy(() => import('@/screens/advertiser/MyCampaigns'))
const CampaignVideo = lazy(() => import('@/screens/advertiser/CampaignVideo'))
const OrdStatus = lazy(() => import('@/screens/advertiser/OrdStatus'))
const AdvertiserFrameworkContract = lazy(() => import('@/screens/advertiser/AdvertiserFrameworkContract'))
const OpenDispute = lazy(() => import('@/screens/shared/OpenDispute'))

// ═══ Campaign Wizard ═══
const CampaignCategory = lazy(() => import('@/screens/advertiser/campaign/CampaignCategory'))
const CampaignChannels = lazy(() => import('@/screens/advertiser/campaign/CampaignChannels'))
const CampaignFormat = lazy(() => import('@/screens/advertiser/campaign/CampaignFormat'))
const CampaignText = lazy(() => import('@/screens/advertiser/campaign/CampaignText'))
const CampaignArbitration = lazy(() => import('@/screens/advertiser/campaign/CampaignArbitration'))
const CampaignWaiting = lazy(() => import('@/screens/advertiser/campaign/CampaignWaiting'))
const CampaignPublished = lazy(() => import('@/screens/advertiser/campaign/CampaignPublished'))

// ═══ Owner screens ═══
const OwnAnalytics = lazy(() => import('@/screens/owner/OwnAnalytics'))
const OwnChannels = lazy(() => import('@/screens/owner/OwnChannels'))
const OwnChannelDetail = lazy(() => import('@/screens/owner/OwnChannelDetail'))
const OwnRequestDetail = lazy(() => import('@/screens/owner/OwnRequestDetail'))
const OwnRequests = lazy(() => import('@/screens/owner/OwnRequests'))
const OwnAddChannel = lazy(() => import('@/screens/owner/OwnAddChannel'))
const OwnChannelSettings = lazy(() => import('@/screens/owner/OwnChannelSettings'))
const OwnPayouts = lazy(() => import('@/screens/owner/OwnPayouts'))
const OwnPayoutRequest = lazy(() => import('@/screens/owner/OwnPayoutRequest'))
const DisputeResponse = lazy(() => import('@/screens/owner/DisputeResponse'))

// ═══ Admin screens ═══
const AdminDashboard = lazy(() => import('@/screens/admin/AdminDashboard'))
const AdminUsersList = lazy(() => import('@/screens/admin/AdminUsersList'))
const AdminDisputesList = lazy(() => import('@/screens/admin/AdminDisputesList'))
const AdminFeedbackList = lazy(() => import('@/screens/admin/AdminFeedbackList'))
const AdminFeedbackDetail = lazy(() => import('@/screens/admin/AdminFeedbackDetail'))
const AdminDisputeDetail = lazy(() => import('@/screens/admin/AdminDisputeDetail'))
const AdminUserDetail = lazy(() => import('@/screens/admin/AdminUserDetail'))
const AdminAccounting = lazy(() => import('@/screens/admin/AdminAccounting'))
const AdminTaxSummary = lazy(() => import('@/screens/admin/AdminTaxSummary'))
const AdminPlatformSettings = lazy(() => import('@/screens/admin/AdminPlatformSettings'))
const AdminPayouts = lazy(() => import('@/screens/admin/AdminPayouts'))

// ═══ Shared screens ═══
const DisputeDetail = lazy(() => import('@/screens/shared/DisputeDetail'))
const MyDisputes = lazy(() => import('@/screens/shared/MyDisputes'))

// ═══ Placeholder screens для MVP ═══
function PlaceholderScreen({ title }: { title: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="text-6xl mb-4">🚧</div>
      <h2 className="text-2xl font-display font-bold text-text-primary mb-2">{title}</h2>
      <p className="text-text-secondary">Этот экран будет добавлен в следующей итерации.</p>
    </div>
  )
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000,
    },
  },
})

const router = createBrowserRouter([
  // ── Public routes ──
  { path: '/login', element: <LoginPage /> },

  // ── Protected routes ──
  {
    element: <AuthGuard />,
    children: [
      // Exempt routes (no PortalShell, no RulesGuard redirect)
      { path: 'accept-rules', element: <AcceptRules /> },
      { path: 'legal-profile-prompt', element: <LegalProfilePrompt /> },
      { path: 'legal-profile', element: <LegalProfileSetup /> },

      // RulesGuard: redirects to /accept-rules if rules not accepted
      {
        element: <RulesGuard />,
        children: [
          {
            element: <PortalShell />,
            children: [
          // Dashboard → redirect to Cabinet
          { index: true, element: <Navigate to="/cabinet" replace /> },

          // Common
          { path: 'cabinet', element: <Cabinet /> },
          { path: 'feedback', element: <Feedback /> },
          { path: 'plans', element: <Plans /> },
          { path: 'topup', element: <TopUp /> },
          { path: 'topup/confirm', element: <TopUpConfirm /> },
          { path: 'referral', element: <Referral /> },
          { path: 'help', element: <Help /> },
          { path: 'billing/history', element: <TransactionHistory /> },
          { path: 'profile/reputation', element: <ReputationHistory /> },
          { path: 'acts', element: <MyActsScreen /> },
          { path: 'legal-profile/view', element: <LegalProfileView /> },
          { path: 'legal-profile/documents', element: <DocumentUpload /> },
          { path: 'contracts', element: <ContractList /> },
          { path: 'contracts/:id', element: <ContractDetail /> },

          // ── Advertiser ──
          // Main redirect
          { path: 'adv', element: <Navigate to="/adv/campaigns" replace /> },

          // Campaigns list
          { path: 'adv/campaigns', element: <MyCampaigns /> },

          // Campaign Wizard
          { path: 'adv/campaigns/new/category', element: <CampaignCategory /> },
          { path: 'adv/campaigns/new/channels', element: <CampaignChannels /> },
          { path: 'adv/campaigns/new/format', element: <CampaignFormat /> },
          { path: 'adv/campaigns/new/text', element: <CampaignText /> },
          { path: 'adv/campaigns/new/terms', element: <CampaignArbitration /> },

          // Campaign lifecycle
          { path: 'adv/campaigns/:id/waiting', element: <CampaignWaiting /> },
          { path: 'adv/campaigns/:id/payment', element: <CampaignPayment /> },
          { path: 'adv/campaigns/:id/counter-offer', element: <CampaignCounterOffer /> },
          { path: 'adv/campaigns/:id/published', element: <CampaignPublished /> },
          { path: 'adv/campaigns/:id/dispute', element: <OpenDispute /> },
          { path: 'adv/disputes', element: <MyDisputes /> },

          // Video & ORD
          { path: 'campaign/video', element: <CampaignVideo /> },
          { path: 'campaign/:id/ord', element: <OrdStatus /> },
          { path: 'contracts/framework', element: <AdvertiserFrameworkContract /> },

          // Analytics
          { path: 'adv/analytics', element: <AdvAnalytics /> },

          // ── Owner ──
          { path: 'own', element: <Navigate to="/own/channels" replace /> },
          { path: 'own/analytics', element: <OwnAnalytics /> },
          { path: 'own/channels', element: <OwnChannels /> },
          { path: 'own/channels/add', element: <OwnAddChannel /> },
          { path: 'own/channels/:id', element: <OwnChannelDetail /> },
          { path: 'own/channels/:id/settings', element: <OwnChannelSettings /> },
          { path: 'own/requests', element: <OwnRequests /> },
          { path: 'own/requests/:id', element: <OwnRequestDetail /> },
          { path: 'own/disputes', element: <MyDisputes /> },
          { path: 'own/disputes/:id', element: <DisputeResponse /> },
          { path: 'own/payouts', element: <OwnPayouts /> },
          { path: 'own/payouts/request', element: <OwnPayoutRequest /> },

          // ── Disputes ──
          { path: 'disputes/:id', element: <DisputeDetail /> },

          // ── Admin ──
          { path: 'admin', element: <AdminDashboard /> },
          { path: 'admin/users', element: <AdminUsersList /> },
          { path: 'admin/users/:id', element: <AdminUserDetail /> },
          { path: 'admin/feedback', element: <AdminFeedbackList /> },
          { path: 'admin/feedback/:id', element: <AdminFeedbackDetail /> },
          { path: 'admin/disputes', element: <AdminDisputesList /> },
          { path: 'admin/disputes/:id', element: <AdminDisputeDetail /> },
          { path: 'admin/payouts', element: <AdminPayouts /> },

          // Admin guarded
          {
            element: <AdminGuard />,
            children: [
              { path: 'admin/accounting', element: <AdminAccounting /> },
              { path: 'admin/tax-summary', element: <AdminTaxSummary /> },
              { path: 'admin/settings', element: <AdminPlatformSettings /> },
            ],
          },

          // Settings
          { path: 'settings', element: <PlaceholderScreen title="Настройки" /> },

          // Catch-all
          { path: '*', element: <NotFoundScreen /> },
        ],
      },
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
