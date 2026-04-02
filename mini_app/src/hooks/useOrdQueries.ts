import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ordApi } from '@/api/ord'

export function useOrdStatus(placementRequestId: number | undefined) {
  return useQuery({
    queryKey: ['ord', placementRequestId],
    queryFn: () => ordApi.getStatus(placementRequestId!),
    enabled: !!placementRequestId,
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' ? 5000 : false,
  })
}

export function useRegisterOrd() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (placementRequestId: number) => ordApi.register(placementRequestId),
    onSuccess: (_, placementRequestId) =>
      qc.invalidateQueries({ queryKey: ['ord', placementRequestId] }),
  })
}
