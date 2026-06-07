import { useQuery } from '@tanstack/react-query'
import { Bell, ChevronLeft, LogOut, Menu, Search } from 'lucide-react'
import { api } from '../lib/api'
import type { CurrentUser, UserSummary } from '../lib/types'
import { initials } from '../lib/utils'
import { ConfirmButton, IconButton, Input } from '../components/ui'
import { useModalFocus } from '../components/useModalFocus'
import { navItems, type ViewKey } from './navigation-model'

export function SideRail({ view, onOpen, onView }: { view: ViewKey; onOpen: () => void; onView: (view: ViewKey) => void }) {
  return (
    <aside className="sidebar-rail" aria-label="Primary navigation">
      <button className="rail-button" aria-label="Open navigation" onClick={onOpen}>
        <Menu size={20} aria-hidden="true" />
      </button>
      <nav className="rail-nav" aria-label="Collapsed workspace navigation">
        {navItems.map((item) => {
          const Icon = item.icon
          const selected = view === item.key
          return (
            <button
              key={item.key}
              className={`rail-nav-button ${selected ? 'active' : ''}`}
              aria-label={item.label}
              aria-current={selected ? 'page' : undefined}
              title={item.label}
              onClick={() => onView(item.key)}
            >
              <Icon size={18} aria-hidden="true" />
            </button>
          )
        })}
      </nav>
      <span className="brand-mark rail-mark">RK</span>
    </aside>
  )
}

export function Sidebar({
  user,
  view,
  onView,
  onClose,
  onLogout,
}: {
  user?: CurrentUser
  view: ViewKey
  onView: (view: ViewKey) => void
  onClose: () => void
  onLogout: () => void
}) {
  const focusScope = useModalFocus<HTMLElement>(true, onClose)

  return (
    <aside {...focusScope} className="sidebar drawer-open" aria-label="Navigation drawer">
      <div className="sidebar-header">
        <div className="brand-row">
          <span className="brand-mark">RK</span>
          <span>Ticketing Tool</span>
        </div>
        <IconButton aria-label="Close navigation" onClick={onClose}>
          <ChevronLeft size={16} aria-hidden="true" />
        </IconButton>
      </div>
      <nav className="nav-list" aria-label="Main">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.key}
              data-testid={`nav-${item.key}`}
              className={`nav-button ${view === item.key ? 'active' : ''}`}
              onClick={() => onView(item.key)}
            >
              <Icon size={17} aria-hidden="true" />
              {item.label}
            </button>
          )
        })}
      </nav>
      <div className="sidebar-footer">
        <Avatar user={user} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="strong small">{user?.display_name ?? 'Loading'}</div>
          <div className="muted small">{user?.is_staff ? 'Staff user' : 'Workspace user'}</div>
        </div>
        <ConfirmButton
          className="icon-button"
          aria-label="Log out"
          title="Log out"
          description="End this browser session and return to authentication."
          confirmLabel="Log out"
          onConfirm={onLogout}
        >
          <LogOut size={16} />
        </ConfirmButton>
      </div>
    </aside>
  )
}

export function Topbar({
  user,
  view,
  onView,
  onOpenNavigation,
}: {
  user?: CurrentUser
  view: ViewKey
  onView: (view: ViewKey) => void
  onOpenNavigation: () => void
}) {
  const notificationsQuery = useQuery({ queryKey: ['notifications'], queryFn: api.notifications })
  const unread = notificationsQuery.data?.filter((item) => !item.read_at).length ?? 0
  const currentLabel = navItems.find((item) => item.key === view)?.label ?? 'Dashboard'
  const unreadLabel = unread === 1 ? '1 unread' : `${unread} unread`
  const unreadBadge = unread > 99 ? '99+' : String(unread)

  return (
    <header className="topbar">
      <div className="topbar-titlebar">
        <IconButton aria-label="Open menu" className="mobile-menu-button" onClick={onOpenNavigation}>
          <Menu size={18} aria-hidden="true" />
        </IconButton>
        <div>
          <div className="muted small">Workspace</div>
          <div className="strong">{currentLabel}</div>
        </div>
      </div>
      <div className="toolbar">
        <div className="search-box">
          <Search size={15} aria-hidden="true" style={{ position: 'absolute', left: 11, top: 11, color: 'var(--muted)' }} />
          <Input style={{ paddingLeft: 34 }} placeholder="Search projects, tasks, people" />
        </div>
        <IconButton
          aria-label={`Notifications, ${unreadLabel}`}
          className="notification-button"
          onClick={() => onView('notifications')}
        >
          <Bell size={16} />
          {unread > 0 && <span className="notification-badge" aria-hidden="true">{unreadBadge}</span>}
        </IconButton>
        <button className="avatar-button" aria-label="Open profile" onClick={() => onView('profile')}>
          <Avatar user={user} />
        </button>
      </div>
    </header>
  )
}

export function Avatar({ user }: { user?: UserSummary }) {
  return <span className="avatar">{initials(user?.display_name ?? 'RK')}</span>
}
