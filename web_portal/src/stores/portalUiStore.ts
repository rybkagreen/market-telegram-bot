import { create } from 'zustand'

export type SidebarMode = 'open' | 'collapsed' | 'closed'

interface BreadcrumbItem {
  label: string
  path?: string
}

interface PortalUiState {
  sidebarMode: SidebarMode
  openSidebar: () => void
  collapseSidebar: () => void
  closeSidebar: () => void
  toggleSidebar: (isDesktop: boolean) => void
  breadcrumbs: BreadcrumbItem[]
  setBreadcrumbs: (items: BreadcrumbItem[]) => void
}

export const usePortalUiStore = create<PortalUiState>()((set) => ({
  sidebarMode: 'collapsed',
  openSidebar: () => set({ sidebarMode: 'open' }),
  collapseSidebar: () => set({ sidebarMode: 'collapsed' }),
  closeSidebar: () => set({ sidebarMode: 'closed' }),
  toggleSidebar: (isDesktop: boolean) => set((s) => {
    if (isDesktop) {
      // Desktop cycle: open → collapsed → open
      return { sidebarMode: s.sidebarMode === 'open' ? 'collapsed' : 'open' }
    }
    // Mobile toggle: closed ↔ open
    return { sidebarMode: s.sidebarMode === 'open' ? 'closed' : 'open' }
  }),
  breadcrumbs: [],
  setBreadcrumbs: (items) => set({ breadcrumbs: items }),
}))
