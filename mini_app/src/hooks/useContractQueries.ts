import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { contractsApi } from '@/api/contracts'
import type { ContractType, SignatureMethod } from '@/lib/types'

export function useContracts(type?: ContractType) {
  return useQuery({
    queryKey: ['contracts', { type }],
    queryFn: () => contractsApi.list(type ? { type } : undefined),
  })
}

export function useContract(id: number) {
  return useQuery({
    queryKey: ['contracts', id],
    queryFn: () => contractsApi.get(id),
    enabled: id > 0,
  })
}

export function useGenerateContract() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ contractType, placementRequestId }: { contractType: ContractType; placementRequestId?: number }) =>
      contractsApi.generate(contractType, placementRequestId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contracts'] }),
  })
}

export function useSignContract() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, method, smsCode }: { id: number; method: SignatureMethod; smsCode?: string }) =>
      contractsApi.sign(id, method, smsCode),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['contracts'] })
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
    },
  })
}

export function useRequestKep() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ contractId, email }: { contractId: number; email: string }) =>
      contractsApi.requestKep(contractId, email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contracts'] }),
  })
}

export function useAcceptRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => contractsApi.acceptRules(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
    },
  })
}
