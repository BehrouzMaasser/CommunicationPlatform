import {
  useRef,
  useState,
} from 'react'
import {
  Link,
  NavLink,
  Outlet,
  useLocation,
} from 'react-router-dom'

import {
  useActivity,
} from '../activity/useActivity'
import {
  logoutCurrentUser,
} from '../api/session'
import {
  useRealtime,
} from '../realtime/RealtimeContext'
import {
  useSession,
} from '../session/useSession'
import Avatar from './users/Avatar'

import type {
  CurrentUser,
} from '../types/users'
import type {
  AuthStatus,
} from '../session/sessionContextState'


type ShellIconName =
  | 'home'
  | 'messages'
  | 'friends'
  | 'groups'
  | 'voice'
  | 'account'


type NavigationItem = {
  to: string
  label: string
  mobileLabel: string
  icon: ShellIconName
  count: number
  countLabel: string
}


function ShellIcon({
  name,
}: {
  name: ShellIconName
}) {
  const paths: Record<ShellIconName, string> = {
    home: 'M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V10.5Z',
    messages: 'M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 3v-3a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm3 5h10V7H7v2Zm0 4h7v-2H7v2Z',
    friends: 'M16 11a4 4 0 1 0-3.95-4.62A5 5 0 1 0 8 14c-3.31 0-6 1.79-6 4v2h10v-2c0-1.05.38-2.02 1.04-2.86A7.7 7.7 0 0 1 16 14c3.31 0 6 1.79 6 4v2h-8v-2c0-1.42-.72-2.72-1.92-3.74A4 4 0 0 0 16 11Z',
    groups: 'M12 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM5.5 6a3.5 3.5 0 0 1 2.24.81A5.95 5.95 0 0 0 8 9.5c0 .37.03.72.1 1.07A3.5 3.5 0 1 1 5.5 6Zm13 0a3.5 3.5 0 1 1-2.6 4.57c.07-.35.1-.7.1-1.07 0-.95-.22-1.86-.62-2.69A3.5 3.5 0 0 1 18.5 6ZM12 12c3.87 0 7 2.24 7 5v3H5v-3c0-2.76 3.13-5 7-5Z',
    voice: 'M12 3a4 4 0 0 0-4 4v5a4 4 0 1 0 8 0V7a4 4 0 0 0-4-4Zm-7 9a1 1 0 0 1 2 0 5 5 0 0 0 10 0 1 1 0 1 1 2 0 7 7 0 0 1-6 6.92V21h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-2.08A7 7 0 0 1 5 12Z',
    account: 'M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-5.33 0-9 2.69-9 6v2h18v-2c0-3.31-3.67-6-9-6Z',
  }

  return (
    <svg
      className="app-shell-icon"
      viewBox="0 0 24 24"
      focusable="false"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  )
}


function ActivityBadge({
  count,
  label,
}: {
  count: number
  label: string
}) {
  if (count <= 0) {
    return null
  }

  return (
    <span
      className="nav-activity-badge"
      aria-label={`${count} ${label}`}
      title={`${count} ${label}`}
    >
      {count > 99 ? '99+' : count}
    </span>
  )
}


function getRealtimeStatusPresentation(
  status: 'connected' | 'connecting' | 'disconnected',
) {
  return {
    label: {
      connected: 'Live',
      connecting: 'Connecting',
      disconnected: 'Offline',
    }[status],
    statusClass: {
      connected: 'is-connected',
      connecting: 'is-connecting',
      disconnected: 'is-disconnected',
    }[status],
  }
}


function RealtimeStatusDot() {
  const { status } = useRealtime()
  const {
    label,
    statusClass,
  } = getRealtimeStatusPresentation(status)

  return (
    <span
      className={`app-realtime-dot ${statusClass}`}
      title={`Realtime status: ${label}`}
      aria-label={`Realtime status: ${label}`}
    />
  )
}


function getSectionTitle(pathname: string) {
  if (pathname === '/') {
    return 'Home'
  }

  if (pathname.startsWith('/messages')) {
    return 'Direct Messages'
  }

  if (pathname.startsWith('/friends')) {
    return 'Friends'
  }

  if (pathname.startsWith('/groups')) {
    return 'Group Chats'
  }

  if (pathname.startsWith('/voice')) {
    return 'Voice Rooms'
  }

  if (pathname.startsWith('/account')) {
    return 'Account'
  }

  return 'Communication Platform'
}


function AccountMenu({
  authStatus,
  currentUser,
  isLoggingOut,
  onLogout,
}: {
  authStatus: AuthStatus
  currentUser: CurrentUser | null
  isLoggingOut: boolean
  onLogout: () => void
}) {
  const detailsRef =
    useRef<HTMLDetailsElement | null>(null)

  function closeMenu() {
    detailsRef.current?.removeAttribute('open')
  }

  if (authStatus === 'loading') {
    return (
      <span className="app-session-label">
        Loading…
      </span>
    )
  }

  if (authStatus === 'anonymous') {
    return (
      <a
        className="btn btn-sm btn-nav-secondary"
        href="/accounts/login/"
      >
        Sign in
      </a>
    )
  }

  if (authStatus === 'error') {
    return (
      <span className="app-session-error">
        Session unavailable
      </span>
    )
  }

  if (!currentUser) {
    return null
  }

  return (
    <details
      ref={detailsRef}
      className="app-account-menu"
    >
      <summary
        className="app-account-menu-trigger"
        aria-label="Open account menu"
      >
        <RealtimeStatusDot />
        <Avatar
          user={currentUser}
          size="sm"
          alt=""
        />
        <span className="app-account-menu-name">
          {currentUser.username}
        </span>
        <span
          className="app-account-menu-chevron"
          aria-hidden="true"
        >
          ▾
        </span>
      </summary>

      <div className="app-account-menu-panel">
        <div className="app-account-menu-identity">
          <Avatar
            user={currentUser}
            size="md"
            alt=""
          />
          <div className="app-account-menu-copy">
            <div className="fw-semibold text-truncate">
              {currentUser.username}
            </div>
            <div className="small text-secondary text-truncate">
              {currentUser.email}
            </div>
          </div>
        </div>

        <Link
          className="app-account-menu-action"
          to="/account"
          onClick={closeMenu}
        >
          <ShellIcon name="account" />
          <span>Account</span>
        </Link>

        <button
          className="app-account-menu-action app-account-menu-signout"
          type="button"
          disabled={isLoggingOut}
          onClick={() => {
            closeMenu()
            onLogout()
          }}
        >
          <span className="app-account-menu-signout-icon" aria-hidden="true">↗</span>
          <span>
            {isLoggingOut
              ? 'Signing out…'
              : 'Sign out'}
          </span>
        </button>
      </div>
    </details>
  )
}


function DesktopSidebar({
  navigationItems,
}: {
  navigationItems: NavigationItem[]
}) {
  return (
    <aside className="app-sidebar" aria-label="Primary navigation">
      <nav className="app-sidebar-nav">
        {navigationItems.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) =>
              `app-sidebar-link${isActive ? ' active' : ''}`
            }
            to={item.to}
            end={item.to === '/'}
          >
            <span className="app-sidebar-link-icon">
              <ShellIcon name={item.icon} />
            </span>
            <span className="app-sidebar-link-label">
              {item.label}
            </span>
            <ActivityBadge
              count={item.count}
              label={item.countLabel}
            />
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}


function MobileBottomNavigation({
  navigationItems,
}: {
  navigationItems: NavigationItem[]
}) {
  return (
    <nav
      className="app-mobile-bottom-nav"
      aria-label="Primary navigation"
    >
      {navigationItems.map((item) => (
        <NavLink
          key={item.to}
          className={({ isActive }) =>
            `app-mobile-bottom-link${isActive ? ' active' : ''}`
          }
          to={item.to}
          end={item.to === '/'}
        >
          <span className="app-mobile-bottom-icon-wrap">
            <ShellIcon name={item.icon} />
            <ActivityBadge
              count={item.count}
              label={item.countLabel}
            />
          </span>
          <span>{item.mobileLabel}</span>
        </NavLink>
      ))}
    </nav>
  )
}


function AppLayoutContent({
  authStatus,
  currentUser,
}: {
  authStatus: AuthStatus
  currentUser: CurrentUser | null
}) {
  const [
    isLoggingOut,
    setIsLoggingOut,
  ] = useState(false)
  const location = useLocation()

  const {
    pendingFriendRequests,
    pendingGroupInvitations,
    pendingVoiceRoomInvitations,
    unreadDirectMessages,
    unreadGroupMessages,
  } = useActivity()

  const groupAttentionCount =
    pendingGroupInvitations
    + unreadGroupMessages

  const navigationItems: NavigationItem[] = [
    {
      to: '/',
      label: 'Home',
      mobileLabel: 'Home',
      icon: 'home',
      count: 0,
      countLabel: '',
    },
    {
      to: '/messages',
      label: 'Direct Messages',
      mobileLabel: 'DMs',
      icon: 'messages',
      count: unreadDirectMessages,
      countLabel: 'unread direct messages',
    },
    {
      to: '/friends',
      label: 'Friends',
      mobileLabel: 'Friends',
      icon: 'friends',
      count: pendingFriendRequests,
      countLabel: 'pending friend requests',
    },
    {
      to: '/groups',
      label: 'Group Chats',
      mobileLabel: 'Groups',
      icon: 'groups',
      count: groupAttentionCount,
      countLabel:
        pendingGroupInvitations > 0
          ? `${unreadGroupMessages} unread messages and ${pendingGroupInvitations} pending invitations`
          : 'unread group messages',
    },
    {
      to: '/voice',
      label: 'Voice Rooms',
      mobileLabel: 'Voice',
      icon: 'voice',
      count: pendingVoiceRoomInvitations,
      countLabel: 'pending Voice Room invitations',
    },
  ]

  async function handleLogout() {
    if (isLoggingOut) {
      return
    }

    setIsLoggingOut(true)

    try {
      await logoutCurrentUser()
      window.location.assign(
        '/accounts/login/',
      )
    } catch {
      setIsLoggingOut(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-brand-region">
          <NavLink
            className="app-brand"
            to="/"
            aria-label="Communication Platform home"
          >
            <span className="app-brand-mark" aria-hidden="true">CP</span>
            <span className="app-brand-name">Communication Platform</span>
          </NavLink>

          <span className="app-mobile-section-title">
            {getSectionTitle(location.pathname)}
          </span>
        </div>

        <div
          className="app-topbar-center"
          data-voice-dock-slot="true"
          aria-hidden="true"
        />

        <div className="app-topbar-account-region">
          <AccountMenu
            authStatus={authStatus}
            currentUser={currentUser}
            isLoggingOut={isLoggingOut}
            onLogout={() => {
              void handleLogout()
            }}
          />
        </div>
      </header>

      <div className="app-shell-body">
        <DesktopSidebar
          navigationItems={navigationItems}
        />

        <main className="app-main">
          <div className="container app-container app-content py-4 py-md-5">
            <Outlet />
          </div>
        </main>
      </div>

      <MobileBottomNavigation
        navigationItems={navigationItems}
      />
    </div>
  )
}


function AppLayout() {
  const {
    authStatus,
    currentUser,
  } = useSession()

  return (
    <AppLayoutContent
      authStatus={authStatus}
      currentUser={currentUser}
    />
  )
}


export default AppLayout
