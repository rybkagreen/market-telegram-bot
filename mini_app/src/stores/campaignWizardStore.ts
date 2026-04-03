// ============================================================
// RekHarbor Mini App — Campaign Wizard Store (Zustand)
// Phase 3 | Multi-step campaign creation state (6 steps)
// ============================================================

import { create } from 'zustand'
import type { Channel, ChannelSettings, PublicationFormat, MediaType } from '@/lib/types'

export type ChannelWithSettings = Channel & { settings: ChannelSettings }

interface CampaignWizardState {
  step: number
  category: string | null
  selectedChannels: ChannelWithSettings[]
  format: PublicationFormat | null
  adText: string
  proposedPrices: Record<number, number>
  /** Full datetime strings in format YYYY-MM-DDTHH:MM (date + time, minimum tomorrow) */
  proposedSchedules: Record<number, string>
  isTest: boolean

  mediaType: MediaType
  videoFileId: string | null
  videoUrl: string | null
  videoDuration: number | null
  videoThumbnailFileId: string | null

  setCategory: (cat: string | null) => void
  toggleChannel: (ch: ChannelWithSettings) => void
  setFormat: (f: PublicationFormat) => void
  setAdText: (text: string) => void
  setProposedPrice: (channelId: number, price: number) => void
  setProposedSchedule: (channelId: number, time: string) => void
  setIsTest: (v: boolean) => void
  setVideo: (video: { fileId: string; url: string; duration: number; thumbnailFileId?: string } | null) => void
  setMediaType: (type: MediaType) => void
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
  isTest: false,
  mediaType: 'none' as MediaType,
  videoFileId: null as string | null,
  videoUrl: null as string | null,
  videoDuration: null as number | null,
  videoThumbnailFileId: null as string | null,
}

export const useCampaignWizardStore = create<CampaignWizardState>()((set, get) => ({
  ...initialState,

  setCategory: (cat) => set({ category: cat, selectedChannels: [] }),

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

  setIsTest: (v) => set({ isTest: v }),

  setVideo: (video) =>
    set(
      video === null
        ? { mediaType: 'none', videoFileId: null, videoUrl: null, videoDuration: null, videoThumbnailFileId: null }
        : { mediaType: 'video', videoFileId: video.fileId, videoUrl: video.url, videoDuration: video.duration, videoThumbnailFileId: video.thumbnailFileId ?? null },
    ),

  setMediaType: (type) => set({ mediaType: type }),

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
