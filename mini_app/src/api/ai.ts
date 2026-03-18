import { api } from './client'
import type { AiTextResult } from '@/lib/types'

export function generateAdText(data: {
  category: string
  channel_names: string[]
  description: string
  max_length?: number
}): Promise<AiTextResult> {
  return api.post('ai/generate-ad-text', { json: data }).json<AiTextResult>()
}
