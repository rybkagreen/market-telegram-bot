import { create } from 'zustand'

interface BreadcrumbItem {
  label: string
  path?: string
}

interface PortalUiState {
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  breadcrumbs: BreadcrumbItem[]
  setBreadcrumbs: (items: BreadcrumbItem[]) => void
}

export const usePortalUiStore = create<PortalUiState>()((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  breadcrumbs: [],
  setBreadcrumbs: (items) => set({ breadcrumbs: items }),
}))
