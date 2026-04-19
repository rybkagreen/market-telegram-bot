import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getMyContracts,
  getContractById,
  signContract,
  acceptRules,
  getPlatformRulesText,
} from '@/api/legal'

// ═══ My Contracts ═══
export function useContracts(type?: string) {
  return useQuery({
    queryKey: ['contracts', type],
    queryFn: () => getMyContracts().then((data) => ({
      items: type ? data.items.filter((c) => c.contract_type === type) : data.items,
    })),
    staleTime: 30_000,
  })
}

// ═══ Contract by ID ═══
export function useContract(id: number) {
  return useQuery({
    queryKey: ['contract', id],
    queryFn: () => getContractById(id),
    enabled: !!id,
  })
}

// ═══ Sign Contract ═══
export function useSignContract() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, method }: { id: number; method: string }) => signContract(id, method),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] })
    },
  })
}

// ═══ Accept Rules ═══
export function useAcceptRules() {
  return useMutation({
    mutationFn: acceptRules,
  })
}

// ═══ Platform Rules Text ═══
export function usePlatformRules() {
  return useQuery({
    queryKey: ['contracts', 'platform-rules', 'text'],
    queryFn: getPlatformRulesText,
    staleTime: 5 * 60_000,
  })
}
