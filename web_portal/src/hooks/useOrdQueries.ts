import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getOrdStatus, registerOrd } from '@/api/ord'

export function useOrdStatus(placementRequestId: number | null | undefined) {
  return useQuery({
    queryKey: ['ord', placementRequestId],
    queryFn: () => getOrdStatus(placementRequestId!),
    enabled: !!placementRequestId,
  })
}

export function useRegisterOrd() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (placementRequestId: number) => registerOrd(placementRequestId),
    onSuccess: (_data, placementRequestId) => {
      queryClient.invalidateQueries({ queryKey: ['ord', placementRequestId] })
    },
  })
}
