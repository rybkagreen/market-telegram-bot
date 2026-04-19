export type { Plan, User, AuthResponse, UserAdminResponse, UserListAdminResponse } from './user'
export type { PlacementStatus, PublicationFormat, MediaType, PlacementRequest } from './placement'
export type { ChannelResponse, Channel } from './channel'
export type {
  DisputeStatus,
  DisputeReason,
  ResolutionAction,
  DisputeDetailResponse,
  DisputeListResponse,
} from './dispute'
export type { PayoutStatus, OrdStatus, TopUpRequest, TopUpResponse, PlanInfo } from './billing'
export type {
  ContractType,
  ContractRole,
  ContractStatus,
  SignatureMethod,
  Contract,
} from './contracts'
export type { LegalStatus, TaxRegime, LegalProfile, LegalProfileCreate, RequiredFields } from './legal'
export type {
  PlatformStatsResponse,
  AdvertiserAnalyticsResponse,
  OwnerAnalyticsResponse,
  ReputationScore,
  ReputationHistoryItem,
  ReputationHistory,
  UserStats,
} from './analytics'
export type {
  Category,
  AiTextResult,
  ReferralStats,
  ReferralItem,
  ReviewResponse,
  PlacementReviewsResponse,
  CreateReviewPayload,
  ChannelSettings,
  ChannelCheckResponse,
  OrdRegistration,
} from './misc'

export interface UserFeedback {
  id: number
  user_id: number
  username: string | null
  text: string
  status: 'new' | 'in_progress' | 'resolved' | 'rejected'
  admin_response: string | null
  created_at: string
  responded_at: string | null
}

export interface FeedbackListResponse {
  items: UserFeedback[]
  total: number
}

export interface FeedbackCreateRequest {
  text: string
}
