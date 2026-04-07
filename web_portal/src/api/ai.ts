import { api } from '@shared/api/client'
import type { AiTextResult } from '@/lib/types/misc'

export async function generateAdText(data: {
  category: string
  channel_names: string[]
  description: string
  max_length?: number
}) {
  return api.post('ai/generate-ad-text', { json: data }).json<AiTextResult>()
}
