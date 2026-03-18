/**
 * AdminLayout — Layout component for admin panel
 * 
 * Features:
 * - Sidebar navigation (desktop)
 * - Main content area
 * - Responsive design
 */

import type { ReactNode } from 'react'
import { ScreenShell } from '@/components/layout/ScreenShell'
import AdminNav from './AdminNav'
import styles from './AdminLayout.module.css'

interface AdminLayoutProps {
  children: ReactNode
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <ScreenShell noPadding className={styles.layout}>
      <aside className={styles.sidebar}>
        <AdminNav />
      </aside>
      <main className={styles.main}>
        {children}
      </main>
    </ScreenShell>
  )
}
