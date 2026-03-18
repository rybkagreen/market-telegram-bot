// ============================================================
// RekHarbor Mini App — Campaign Wizard Store (Zustand)
// Phase 3 | Multi-step campaign creation state (6 steps)
// ============================================================

import { create } from 'zustand'
import type { Channel, ChannelSettings, PublicationFormat } from '@/lib/types'

export type ChannelWithSettings = Channel & { settings: ChannelSettings }

interface CampaignWizardState {
  step: number
  category: string | null
  selectedChannels: ChannelWithSettings[]
  format: PublicationFormat | null
  adText: string
  proposedPrices: Record<number, number>
  proposedSchedules: Record<number, string>

  setCategory: (cat: string) => void
  toggleChannel: (ch: ChannelWithSettings) => void
  setFormat: (f: PublicationFormat) => void
  setAdText: (text: string) => void
  setProposedPrice: (channelId: number, price: number) => void
  setProposedSchedule: (channelId: number, time: string) => void
  nextStep: () => void
  prevStep: () => void
  reset: () => void
  getTotalPrice: () => number
}

const initialState = {
  step: 1,
  category: null,
  selectedChannels: [] as ChannelWithSettings[],
  format: null as PublicationFormat | null,
  adText: '',
  proposedPrices: {} as Record<number, number>,
  proposedSchedules: {} as Record<number, string>,
}

export const useCampaignWizardStore = create<CampaignWizardState>()((set, get) => ({
  ...initialState,

  setCategory: (cat) => set({ category: cat }),

  toggleChannel: (ch) =>
    set((state) => {
      const exists = state.selectedChannels.some((c) => c.id === ch.id)
      return {
        selectedChannels: exists
          ? state.selectedChannels.filter((c) => c.id !== ch.id)
          : [...state.selectedChannels, ch],
      }
    }),

  setFormat: (f) => set({ format: f }),

  setAdText: (text) => set({ adText: text }),

  setProposedPrice: (channelId, price) =>
    set((state) => ({
      proposedPrices: { ...state.proposedPrices, [channelId]: price },
    })),

  setProposedSchedule: (channelId, time) =>
    set((state) => ({
      proposedSchedules: { ...state.proposedSchedules, [channelId]: time },
    })),

  nextStep: () => set((state) => ({ step: Math.min(state.step + 1, 6) })),
  prevStep: () => set((state) => ({ step: Math.max(state.step - 1, 1) })),

  reset: () => set(initialState),

  getTotalPrice: () => {
    const { selectedChannels, proposedPrices } = get()
    return selectedChannels.reduce((sum, ch) => sum + (proposedPrices[ch.id] ?? 0), 0)
  },
}))
