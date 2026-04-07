import { useMutation } from '@tanstack/react-query'
import { generateAdText } from '@/api/ai'

export function useGenerateAdText() {
  return useMutation({
    mutationFn: generateAdText,
  })
}
