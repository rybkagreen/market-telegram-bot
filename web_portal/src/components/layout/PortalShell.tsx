import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useMediaQuery, breakpoints } from '@shared/hooks/useMediaQuery'
import { usePortalUiStore } from '@/stores/portalUiStore'
import { useNeedsAcceptRules } from '@/hooks/useUserQueries'
import { Notification, Button } from '@shared/ui'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

export function PortalShell() {
  const { sidebarMode, closeSidebar } = usePortalUiStore()
  const isDesktop = useMediaQuery(breakpoints.md)
  const location = useLocation()
  const navigate = useNavigate()

  const isOpen = sidebarMode === 'open'

  useEffect(() => {
    if (!isDesktop && sidebarMode !== 'closed') {
      closeSidebar()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDesktop])

  const { data: acceptRules } = useNeedsAcceptRules()
  const showAcceptRulesBanner =
    acceptRules?.needs_accept === true && !location.pathname.startsWith('/accept-rules')

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
        <main className="flex-1 overflow-y-auto scrollbar-thin bg-harbor-bg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-4">
            {showAcceptRulesBanner && (
              <Notification type="warning">
                <div className="flex items-center justify-between gap-3 w-full">
                  <span className="text-sm">
                    Примите правила платформы и политику конфиденциальности, чтобы продолжить работу.
                  </span>
                  <Button size="sm" variant="primary" onClick={() => navigate('/accept-rules')}>
                    Принять
                  </Button>
                </div>
              </Notification>
            )}
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
