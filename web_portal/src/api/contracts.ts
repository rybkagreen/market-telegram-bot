// ============================================================
// RekHarbor Web Portal — Contracts API Client
// S31-04 | GET /api/contracts/* endpoints
// ============================================================

import { api } from '@shared/api/client'
import type { Contract } from '@/lib/types'

export interface ContractListResponse {
  items: Contract[]
  total: number
}

export const getMyContracts = (): Promise<ContractListResponse> =>
  api.get('contracts/mine').json<ContractListResponse>()

export const getContractById = (contractId: number): Promise<Contract> =>
  api.get(`contracts/${contractId}`).json<Contract>()

export const getContractsByPlacement = (placementRequestId: number): Promise<ContractListResponse> =>
  api.get(`contracts/by-placement/${placementRequestId}`).json<ContractListResponse>()
