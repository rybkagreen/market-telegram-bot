import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyLegalProfile, createLegalProfile, updateLegalProfile, skipLegalPrompt, validateInn, getRequiredFields, validateEntity } from '@/api/legal'

// ═══ My Legal Profile ═══
export function useMyLegalProfile() {
  return useQuery({
    queryKey: ['legal-profile', 'me'],
    queryFn: getMyLegalProfile,
    staleTime: 60_000,
  })
}

// ═══ Create Legal Profile ═══
export function useCreateLegalProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createLegalProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['legal-profile', 'me'] })
    },
  })
}

// ═══ Update Legal Profile ═══
export function useUpdateLegalProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateLegalProfile,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['legal-profile', 'me'] })
    },
  })
}

// ═══ Skip Legal Prompt ═══
export function useSkipLegalPrompt() {
  return useMutation({
    mutationFn: skipLegalPrompt,
  })
}

// ═══ Validate INN ═══
export function useValidateInn() {
  return useMutation({
    mutationFn: (inn: string) => validateInn(inn),
  })
}

// ═══ Required Fields by Legal Status ═══
export function useRequiredFields(legalStatus: string | undefined) {
  return useQuery({
    queryKey: ['legal-profile', 'required-fields', legalStatus],
    queryFn: () => getRequiredFields(legalStatus!),
    enabled: !!legalStatus,
  })
}

// ═══ Validate Entity (INN + OGRN checksums via FNS) ═══
export function useValidateEntity() {
  return useMutation({
    mutationFn: (data: { legal_status: string; inn: string; legal_name?: string; kpp?: string; ogrn?: string; ogrnip?: string; passport_series?: string; passport_number?: string }) =>
      validateEntity(data),
  })
}
