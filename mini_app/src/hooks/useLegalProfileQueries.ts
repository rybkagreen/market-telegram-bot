import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { legalProfileApi } from '@/api/legalProfile'
import type { LegalProfileCreate, LegalStatus } from '@/lib/types'

export function useMyLegalProfile() {
  return useQuery({
    queryKey: ['legal-profile', 'me'],
    queryFn: () => legalProfileApi.getMyProfile(),
  })
}

export function useRequiredFields(legalStatus: LegalStatus | undefined) {
  return useQuery({
    queryKey: ['legal-profile', 'required-fields', legalStatus],
    queryFn: () => legalProfileApi.getRequiredFields(legalStatus!),
    enabled: !!legalStatus,
  })
}

export function useCreateLegalProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LegalProfileCreate) => legalProfileApi.createProfile(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['legal-profile'] })
      qc.invalidateQueries({ queryKey: ['user', 'me'] })
    },
  })
}

export function useUpdateLegalProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<LegalProfileCreate>) => legalProfileApi.updateProfile(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['legal-profile'] }),
  })
}

export function useValidateInn() {
  return useMutation({
    mutationFn: (inn: string) => legalProfileApi.validateInn(inn),
  })
}

export function useSkipLegalPrompt() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => legalProfileApi.skipLegalPrompt(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user', 'me'] }),
  })
}
