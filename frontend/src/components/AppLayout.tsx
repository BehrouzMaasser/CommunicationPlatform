import {
  useEffect,
  useState,
} from 'react'
import {
  NavLink,
  Outlet,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import {
  ActivityProvider,
} from '../activity/ActivityContext'
import {
  useActivity,
} from '../activity/useActivity'
import {
  getCurrentUser,
  logoutCurrentUser,
} from '../api/session'
import {
  RealtimeProvider,
  useRealtime,
} from '../realtime/RealtimeContext'

import type {
  CurrentUser,
} from '../types/users'


type AuthStatus =
  | 'loading'
  | 'authenticated'
  | 'anonymous'
  | 'error'


const navLinkClass = ({
  isActive,
}: {
  isActive: boolean
}) =>
  `nav-link${
    isActive ? ' active' : ''
  }`


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
    badgeClass: {
      connected: 'text-bg-success',
      connecting: 'text-bg-warning',
      disconnected: 'text-bg-secondary',
    }[status],
  }
}


function RealtimeStatusBadge() {
  const { status } =
    useRealtime()
  const {
    label,
    badgeClass,
  } = getRealtimeStatusPresentation(status)

  return (
    <span
      className={`connection-status ${badgeClass}`}
      title={`Realtime status: ${label}`}
      aria-label={`Realtime status: ${label}`}
    >
      <span className="connection-status-dot" aria-hidden="true" />
      <span className="d-none d-xl-inline">{label}</span>
    </span>
  )
}


function MobileAccountNav({
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
  const { status } =
    useRealtime()
  const {
    label,
    badgeClass,
  } = getRealtimeStatusPresentation(status)

  return (
    <div className="app-mobile-account-nav d-flex d-sm-none">
      {authStatus === 'authenticated' && currentUser && (
        <>
          <a
            className="app-mobile-user-link"
            href="/accounts/me/"
            title={`${currentUser.username} · ${label}`}
          >
            <span
              className={`connection-status mobile-connection-status ${badgeClass}`}
              aria-label={`Realtime status: ${label}`}
            >
              <span className="connection-status-dot" aria-hidden="true" />
            </span>
            <strong>{currentUser.username}</strong>
          </a>

          <details className="app-mobile-account-menu">
            <summary aria-label="Open account menu">
              <span aria-hidden="true">⋮</span>
            </summary>
            <div className="app-mobile-account-menu-panel">
              <a href="/accounts/me/">Account</a>
              <button
                type="button"
                disabled={isLoggingOut}
                onClick={onLogout}
              >
                {isLoggingOut ? 'Signing out…' : 'Sign out'}
              </button>
            </div>
          </details>
        </>
      )}

      {authStatus === 'loading' && (
        <span className="app-session-label ms-auto">Loading…</span>
      )}

      {authStatus === 'anonymous' && (
        <a className="app-mobile-sign-in ms-auto" href="/accounts/login/">
          Sign in
        </a>
      )}

      {authStatus === 'error' && (
        <span className="app-session-error ms-auto">Session unavailable</span>
      )}
    </div>
  )
}


function AppLayoutContent({
  authStatus,
  currentUser,
}: {
  authStatus: AuthStatus
  currentUser:
    CurrentUser | null
}) {
  const [
    isLoggingOut,
    setIsLoggingOut,
  ] = useState(false)

  const {
    pendingFriendRequests,
    pendingGroupInvitations,
    unreadDirectMessages,
    unreadGroupMessages,
  } = useActivity()

  const groupAttentionCount =
    pendingGroupInvitations
    + unreadGroupMessages

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
      <nav className="navbar app-navbar sticky-top">
        <div className="container app-container app-navbar-inner">
          <NavLink
            className="navbar-brand app-brand"
            to="/"
            aria-label="Communication Platform home"
          >
            <span className="app-brand-mark" aria-hidden="true">CP</span>
            <span className="app-brand-name">Communication Platform</span>
          </NavLink>

          <MobileAccountNav
            authStatus={authStatus}
            currentUser={currentUser}
            isLoggingOut={isLoggingOut}
            onLogout={() => {
              void handleLogout()
            }}
          />

          <div className="navbar-nav app-main-nav flex-row">
            <NavLink
              className={
                navLinkClass
              }
              to="/friends"
            >
              <span>Friends</span>
              <ActivityBadge
                count={pendingFriendRequests}
                label="pending friend requests"
              />
            </NavLink>

            <NavLink
              className={
                navLinkClass
              }
              to="/messages"
            >
              <span>Messages</span>
              <ActivityBadge
                count={unreadDirectMessages}
                label="unread direct messages"
              />
            </NavLink>

            <NavLink
              className={
                navLinkClass
              }
              to="/groups"
            >
              <span>Groups</span>
              <ActivityBadge
                count={groupAttentionCount}
                label={
                  pendingGroupInvitations > 0
                    ? `${unreadGroupMessages} unread messages and ${pendingGroupInvitations} pending invitations`
                    : 'unread group messages'
                }
              />
            </NavLink>
          </div>

          <div className="app-account-nav ms-auto d-none d-sm-flex align-items-center gap-2">
            {authStatus ===
              'authenticated' && (
              <RealtimeStatusBadge />
            )}

            {authStatus ===
              'loading' && (
              <span className="app-session-label">
                Loading…
              </span>
            )}

            {authStatus ===
              'authenticated' &&
              currentUser && (
                <span className="app-user-chip d-none d-md-inline-flex">
                  <span className="app-user-avatar" aria-hidden="true">
                    {currentUser.username.charAt(0).toUpperCase()}
                  </span>
                  <strong>{currentUser.username}</strong>
                </span>
              )}

            {authStatus ===
              'authenticated' && (
                <>
                  <a
                    className="btn btn-sm btn-nav-secondary"
                    href="/accounts/me/"
                  >
                    Account
                  </a>

                  <button
                    className="btn btn-sm btn-nav-primary"
                    type="button"
                    disabled={
                      isLoggingOut
                    }
                    onClick={() => {
                      void handleLogout()
                    }}
                  >
                    {isLoggingOut
                      ? 'Signing out…'
                      : 'Sign out'}
                  </button>
                </>
              )}

            {authStatus ===
              'anonymous' && (
              <a
                className="btn btn-sm btn-nav-secondary"
                href="/accounts/login/"
              >
                Sign in
              </a>
            )}

            {authStatus ===
              'error' && (
              <span className="app-session-error">
                Session unavailable
              </span>
            )}
          </div>
        </div>
      </nav>

      <main className="container app-container app-main py-4 py-md-5">
        <Outlet />
      </main>
    </div>
  )
}


function AppLayout() {
  const [
    currentUser,
    setCurrentUser,
  ] =
    useState<CurrentUser | null>(
      null,
    )

  const [
    authStatus,
    setAuthStatus,
  ] =
    useState<AuthStatus>(
      'loading',
    )

  useEffect(() => {
    let cancelled = false

    async function loadCurrentUser() {
      try {
        const user =
          await getCurrentUser()

        if (cancelled) {
          return
        }

        setCurrentUser(user)
        setAuthStatus(
          'authenticated',
        )
      } catch (error) {
        if (cancelled) {
          return
        }

        if (
          error instanceof
            ApiError &&
          error.status === 401
        ) {
          setCurrentUser(null)
          setAuthStatus(
            'anonymous',
          )
          return
        }

        setCurrentUser(null)
        setAuthStatus('error')
      }
    }

    void loadCurrentUser()

    return () => {
      cancelled = true
    }
  }, [])

  return (
    <RealtimeProvider
      enabled={
        authStatus ===
        'authenticated'
      }
      currentUserId={
        currentUser?.id
      }
    >
      <ActivityProvider
        enabled={
          authStatus ===
          'authenticated'
        }
        currentUserId={
          currentUser?.id
        }
      >
        <AppLayoutContent
          authStatus={authStatus}
          currentUser={currentUser}
        />
      </ActivityProvider>
    </RealtimeProvider>
  )
}


export default AppLayout
