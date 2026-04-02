import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as Sentry from '@sentry/react'
import { createFeedback, getMyFeedback } from '@/api/feedback'
import { useUiStore } from '@/stores/uiStore'

/**
 * Get current user's feedback history
 */
export const useMyFeedback = () =>
  useQuery({
    queryKey: ['feedback', 'my'],
    queryFn: getMyFeedback,
    staleTime: 5 * 60_000, // 5 minutes
    retry: 2,
  })

/**
 * Create new feedback
 */
export const useCreateFeedback = () => {
  const queryClient = useQueryClient()
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (text: string) => createFeedback(text),
    onSuccess: () => {
      // Invalidate feedback list to refetch
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
      addToast('success', '✅ Обратная связь отправлена!')
    },
    onError: (error) => {
      Sentry.captureException(error)
      addToast('error', '❌ Ошибка при отправке. Попробуйте позже.')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['feedback'] })
    },
  })
}
