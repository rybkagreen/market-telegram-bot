import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useMediaQuery, breakpoints } from '@shared/hooks/useMediaQuery'
import { usePortalUiStore } from '@/stores/portalUiStore'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function PortalShell() {
  const { sidebarMode, closeSidebar } = usePortalUiStore()
  const isDesktop = useMediaQuery(breakpoints.md)

  const isOpen = sidebarMode === 'open'

  useEffect(() => {
    if (!isDesktop && sidebarMode !== 'closed') {
      closeSidebar()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDesktop])

  return (
    <div className="flex h-dvh overflow-hidden bg-harbor-bg">
      {/* Mobile overlay */}
      {!isDesktop && isOpen && (
        <button
          type="button"
          onClick={closeSidebar}
          className="fixed inset-0 bg-black/50 z-[60] cursor-default"
          aria-label="Закрыть меню"
        />
      )}

      {/* Sidebar — absolute on mobile, static on desktop */}
      <div
        className={`z-[70] md:static fixed inset-y-0 left-0 transition-transform duration-300 ${
          !isDesktop && !isOpen ? '-translate-x-full' : 'translate-x-0'
        }`}
      >
        <Sidebar />
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-x-hidden overflow-y-scroll scrollbar-thin bg-harbor-bg [scrollbar-gutter:stable] overscroll-contain">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
