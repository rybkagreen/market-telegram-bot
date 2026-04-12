import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type SidebarMode = 'open' | 'collapsed' | 'closed'

// SSR-safe desktop detection
function isDesktopScreen(): boolean {
  return typeof window !== 'undefined' && window.innerWidth >= 768
}

// Compute initial sidebar mode based on screen size
function getInitialSidebarMode(): SidebarMode {
  if (typeof window === 'undefined') {
    return 'closed' // SSR fallback
  }
  return isDesktopScreen() ? 'collapsed' : 'closed'
}

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

export const usePortalUiStore = create<PortalUiState>()(
  persist(
    (set) => ({
      sidebarMode: getInitialSidebarMode(),
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
    }),
    {
      name: 'rekharbor-portal-ui',
      partialize: (state) => ({ sidebarMode: state.sidebarMode }),
    }
  )
)
