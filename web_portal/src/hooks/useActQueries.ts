import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyActs, signAct, getActPdfBlob } from '@/api/acts'

export function useMyActs(params?: { limit?: number; placementRequestId?: number }) {
  return useQuery({
    queryKey: ['acts', 'mine', params],
    queryFn: () => getMyActs(params),
    staleTime: 30_000,
  })
}

export function useSignAct() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (actId: number) => signAct(actId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['acts'] })
    },
  })
}

export async function downloadActPdf(actId: number): Promise<void> {
  const blob = await getActPdfBlob(actId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `act_${actId}.pdf`
  a.click()
  URL.revokeObjectURL(url)
}
