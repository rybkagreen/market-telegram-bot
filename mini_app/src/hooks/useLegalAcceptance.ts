import { useMutation, useQueryClient } from '@tanstack/react-query'
import { legalAcceptanceApi } from '@/api/legal-acceptance'

/**
 * Phase 1 §1.B.2 carve-out — accepts platform rules + privacy policy.
 *
 * Migrated out of `useContractQueries.ts` (deleted in §1.B.2). The hook
 * itself is unchanged — same mutation surface, same invalidation behaviour.
 */
export function useAcceptRules() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => legalAcceptanceApi.acceptRules(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
      qc.invalidateQueries({ queryKey: ['user', 'needs-accept-rules'] })
    },
  })
}
