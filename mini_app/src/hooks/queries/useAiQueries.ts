import { useMutation } from '@tanstack/react-query'
import { generateAdText } from '@/api/ai'
import { useUiStore } from '@/stores/uiStore'

export const useGenerateAdText = () => {
  const addToast = useUiStore((s) => s.addToast)

  return useMutation({
    mutationFn: (data: {
      category: string
      channel_names: string[]
      description: string
      max_length?: number
    }) => generateAdText(data),
    onError: () => {
      addToast('error', 'Ошибка при генерации текста')
    },
  })
}
