import { api } from './client'
import type { Category } from '@/lib/types'

export function getCategories(): Promise<Category[]> {
  return api.get('categories/').json<Category[]>()
}
