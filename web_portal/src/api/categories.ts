import { api } from '@shared/api/client'
import type { Category } from '@/lib/types/misc'

export async function getCategories() {
  return api.get('categories/').json<Category[]>()
}
