import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  uploadDocument,
  getUploadStatus,
  getPassportCompleteness,
} from '@/api/documents'

export function usePassportCompleteness(enabled: boolean = true) {
  return useQuery({
    queryKey: ['documents', 'passport-completeness'],
    queryFn: getPassportCompleteness,
    staleTime: 30_000,
    enabled,
  })
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      file,
      documentType,
      passportPageGroup,
    }: {
      file: File
      documentType: string
      passportPageGroup?: string
    }) => uploadDocument(file, documentType, passportPageGroup),
    onSuccess: (_data, { documentType }) => {
      if (documentType === 'passport') {
        queryClient.invalidateQueries({ queryKey: ['documents', 'passport-completeness'] })
      }
    },
  })
}

export function useUploadStatus(uploadId: number | null, enabled: boolean = true) {
  return useQuery({
    queryKey: ['documents', 'status', uploadId],
    queryFn: () => getUploadStatus(uploadId!),
    enabled: !!uploadId && enabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      if (status === 'completed' || status === 'failed' || status === 'unreadable') return false
      return 5_000
    },
  })
}
