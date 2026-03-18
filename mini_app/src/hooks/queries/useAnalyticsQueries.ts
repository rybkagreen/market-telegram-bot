// ВАЖНО (RT-001): advertiser и owner — это РАЗНЫЕ endpoint-ы с РАЗНЫМИ данными!
// Никогда не перепутывать их местами. Используйте РАЗНЫЕ queryKey для каждого!

import { useQuery } from '@tanstack/react-query'
import { getAdvertiserAnalytics, getOwnerAnalytics } from '@/api/analytics'

// Примечание (UX-P0): onError логирование реализовано на уровне компонентов
// (AdvAnalytics.tsx, OwnAnalytics.tsx) так как React Query v5 не поддерживает
// onError в useQuery options напрямую

export const useAdvertiserAnalytics = () =>
  useQuery({
    queryKey: ['analytics', 'advertiser'],
    queryFn: getAdvertiserAnalytics,
    staleTime: 5 * 60_000,
    retry: 2, // ИЗМЕНЕНО (UX-P0): уменьшено с 3 до 2 для быстрой ошибки
  })

export const useOwnerAnalytics = () =>
  useQuery({
    queryKey: ['analytics', 'owner'],
    queryFn: getOwnerAnalytics,
    staleTime: 5 * 60_000,
    retry: 2, // ИЗМЕНЕНО (UX-P0): уменьшено с 3 до 2 для быстрой ошибки
  })
