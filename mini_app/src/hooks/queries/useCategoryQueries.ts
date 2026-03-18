import { useQuery } from '@tanstack/react-query'
import { getCategories } from '@/api/categories'

export const useCategories = () =>
  useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: 60 * 60_000,
  })
