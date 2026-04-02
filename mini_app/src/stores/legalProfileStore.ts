import { create } from 'zustand'
import type { LegalStatus, LegalProfileCreate } from '@/lib/types'

interface LegalProfileState {
  currentStep: number
  formData: Partial<LegalProfileCreate>
  selectedStatus: LegalStatus | null
  setStep: (step: number) => void
  setSelectedStatus: (status: LegalStatus) => void
  updateFormData: (data: Partial<LegalProfileCreate>) => void
  reset: () => void
}

export const useLegalProfileStore = create<LegalProfileState>((set) => ({
  currentStep: 0,
  formData: {},
  selectedStatus: null,
  setStep: (step) => set({ currentStep: step }),
  setSelectedStatus: (status) => set({ selectedStatus: status, formData: { legal_status: status } }),
  updateFormData: (data) => set((state) => ({ formData: { ...state.formData, ...data } })),
  reset: () => set({ currentStep: 0, formData: {}, selectedStatus: null }),
}))
