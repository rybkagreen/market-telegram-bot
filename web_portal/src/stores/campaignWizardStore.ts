import { create } from 'zustand'

export type PublicationFormat = 'post_24h' | 'post_48h' | 'post_7d' | 'pin_24h' | 'pin_48h'

export interface ChannelWithSettings {
  id: number
  title: string
  username: string | null
  member_count: number
  category: string
  settings: {
    price_per_post: string
  }
}

interface CampaignWizardState {
  step: number
  category: string | null
  selectedChannels: ChannelWithSettings[]
  format: PublicationFormat | null
  adText: string
  proposedPrices: Record<number, number>
  proposedSchedules: Record<number, string>
  isTest: boolean
  mediaType: string
  videoFileId: string | null
  videoUrl: string | null
  videoDuration: number | null

  setCategory: (cat: string | null) => void
  toggleChannel: (ch: ChannelWithSettings) => void
  setFormat: (f: PublicationFormat) => void
  setAdText: (text: string) => void
  setProposedPrice: (channelId: number, price: number) => void
  setProposedSchedule: (channelId: number, time: string) => void
  setIsTest: (v: boolean) => void
  setVideo: (video: { fileId: string; url: string; duration: number } | null) => void
  setMediaType: (type: string) => void
  nextStep: () => void
  prevStep: () => void
  reset: () => void
  getTotalPrice: () => number
}

const initialState = {
  step: 1,
  category: null as string | null,
  selectedChannels: [] as ChannelWithSettings[],
  format: null as PublicationFormat | null,
  adText: '',
  proposedPrices: {} as Record<number, number>,
  proposedSchedules: {} as Record<number, string>,
  isTest: false,
  mediaType: 'none',
  videoFileId: null as string | null,
  videoUrl: null as string | null,
  videoDuration: null as number | null,
}

export const useCampaignWizardStore = create<CampaignWizardState>()((set, get) => ({
  ...initialState,

  setCategory: (cat) => set({ category: cat, selectedChannels: [] }),

  toggleChannel: (ch) =>
    set((state) => ({
      selectedChannels: state.selectedChannels.some((c) => c.id === ch.id)
        ? state.selectedChannels.filter((c) => c.id !== ch.id)
        : [...state.selectedChannels, ch],
    })),

  setFormat: (f) => set({ format: f }),

  setAdText: (text) => set({ adText: text }),

  setIsTest: (v) => set({ isTest: v }),

  setVideo: (video) =>
    set(
      video === null
        ? { mediaType: 'none', videoFileId: null, videoUrl: null, videoDuration: null }
        : { mediaType: 'video', videoFileId: video.fileId, videoUrl: video.url, videoDuration: video.duration },
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
