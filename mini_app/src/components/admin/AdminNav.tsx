/**
 * AdminNav — Navigation component for admin panel
 * 
 * Features:
 * - Navigation between admin sections
 * - Active section highlighting
 * - Icons for each section
 */

import { NavLink } from 'react-router-dom'
import styles from './AdminNav.module.css'

const navItems = [
  { path: '/admin', label: 'Dashboard', icon: '📊' },
  { path: '/admin/feedback', label: 'Feedback', icon: '💬' },
  { path: '/admin/disputes', label: 'Disputes', icon: '⚖️' },
  { path: '/admin/users', label: 'Users', icon: '👥' },
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
          <span className={styles.icon}>{item.icon}</span>
          <span className={styles.label}>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
