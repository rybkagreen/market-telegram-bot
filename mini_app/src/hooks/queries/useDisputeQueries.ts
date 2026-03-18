import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyDisputes, getDispute, createDispute, replyToDispute } from '@/api/disputes'
import type { Dispute, DisputeReason } from '@/lib/types'
import { useUiStore } from '@/stores/uiStore'

export const useMyDisputes = () =>
  useQuery({
    queryKey: ['disputes'],
    queryFn: getMyDisputes,
    staleTime: 60_000,
  })

export const useDispute = (id: number | null) =>
  useQuery({
    queryKey: ['disputes', id],
    queryFn: () => getDispute(id!),
    enabled: !!id,
  })

export const useCreateDispute = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (data: { placement_id: number; reason: DisputeReason; comment: string }) =>
      createDispute(data),
    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: ['disputes'] })
      const previousDisputes = queryClient.getQueryData<Dispute[]>(['disputes'])
      return { previousDisputes, data }
    },
    onError: (_err, _vars, context) => {
      if (context?.previousDisputes) {
        queryClient.setQueryData(['disputes'], context.previousDisputes)
      }
      addToast('error', 'Ошибка при создании диспута')
    },
    onSuccess: () => {
      addToast('success', 'Диспут открыт')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['disputes'] })
      queryClient.invalidateQueries({ queryKey: ['placements'] })
    },
  })
}

export const useReplyToDispute = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: ({ id, comment }: { id: number; comment: string }) => replyToDispute(id, comment),
    onSuccess: () => {
      addToast('success', 'Ответ отправлен')
    },
    onError: () => {
      addToast('error', 'Ошибка при отправке ответа')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['disputes'] })
    },
  })
}
