import { NavLink } from 'react-router-dom'

const items = [
  { to: '/',          icon: '🏠', label: 'Главная'   },
  { to: '/campaigns', icon: '📊', label: 'Кампании'  },
  { to: '/analytics', icon: '📈', label: 'Аналитика' },
  { to: '/channels',  icon: '📡', label: 'База'       },
  { to: '/billing',   icon: '💳', label: 'Баланс'    },
]

export function BottomNav() {
  const haptic = () => {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('light')
  }

  return (
    <nav className="bottom-nav">
      {items.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            isActive ? 'nav-item nav-item-active' : 'nav-item'
          }
          onClick={haptic}
        >
          <span style={{ fontSize: 20, lineHeight: 1 }}>{icon}</span>
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
