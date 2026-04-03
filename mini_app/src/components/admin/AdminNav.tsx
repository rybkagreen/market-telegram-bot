/**
 * AdminNav — Navigation component for admin panel
 *
 * Features:
 * - Navigation between admin sections
 * - Active section highlighting
 * - Icons via lucide-react (Icon component)
 */

import { NavLink } from 'react-router-dom'
import { Icon } from '@/components/ui/Icon'
import styles from './AdminNav.module.css'

const navItems = [
  { path: '/admin', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/admin/feedback', label: 'Feedback', icon: 'MessageSquare' },
  { path: '/admin/disputes', label: 'Disputes', icon: 'Scale' },
  { path: '/admin/users', label: 'Users', icon: 'Users' },
  { path: '/admin/accounting', label: 'Бухгалтерия', icon: 'BookOpen' },
  { path: '/admin/tax-summary', label: 'Налоги', icon: 'Receipt' },
  { path: '/admin/settings', label: 'Реквизиты', icon: 'Building2' },
]

export default function AdminNav() {
  return (
    <nav className={styles.nav}>
      {navItems.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            `${styles.navItem} ${isActive ? styles.active : ''}`
          }
        >
          <span className={styles.icon}>
            <Icon name={item.icon} size={18} />
          </span>
          <span className={styles.label}>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
