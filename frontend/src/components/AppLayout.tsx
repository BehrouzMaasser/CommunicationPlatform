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


function RealtimeStatusBadge() {
  const { status } =
    useRealtime()

  const label = {
    connected: 'Live',
    connecting: 'Connecting',
    disconnected: 'Offline',
  }[status]

  const badgeClass = {
    connected:
      'text-bg-success',
    connecting:
      'text-bg-warning',
    disconnected:
      'text-bg-secondary',
  }[status]

  return (
    <span
      className={`badge ${badgeClass}`}
      title="Realtime connection status"
    >
      {label}
    </span>
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
      <nav className="navbar navbar-expand-lg bg-dark border-bottom border-body">
        <div className="container">
          <NavLink
            className="navbar-brand text-white fw-semibold"
            to="/"
          >
            CommunicationPlatform
          </NavLink>

          <div className="navbar-nav flex-row gap-2 gap-md-3">
            <NavLink
              className={
                navLinkClass
              }
              to="/friends"
            >
              Friends
            </NavLink>

            <NavLink
              className={
                navLinkClass
              }
              to="/messages"
            >
              Messages
            </NavLink>

            <NavLink
              className={
                navLinkClass
              }
              to="/groups"
            >
              Groups
            </NavLink>
          </div>

          <div className="ms-auto ps-3 text-white d-flex align-items-center gap-2">
            {authStatus ===
              'authenticated' && (
              <RealtimeStatusBadge />
            )}

            {authStatus ===
              'loading' && (
              <span className="text-white-50">
                Checking session…
              </span>
            )}

            {authStatus ===
              'authenticated' &&
              currentUser && (
                <span>
                  Signed in as{' '}
                  <strong>
                    {
                      currentUser
                        .username
                    }
                  </strong>
                </span>
              )}

            {authStatus ===
              'authenticated' && (
                <>
                  <a
                    className="btn btn-sm btn-outline-light"
                    href="/accounts/me/"
                  >
                    Account
                  </a>

                  <button
                    className="btn btn-sm btn-light"
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
                className="btn btn-sm btn-outline-light"
                href="/accounts/login/"
              >
                Sign in
              </a>
            )}

            {authStatus ===
              'error' && (
              <span className="text-warning">
                Could not check session
              </span>
            )}
          </div>
        </div>
      </nav>

      <main className="container py-4 py-md-5">
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
      <AppLayoutContent
        authStatus={authStatus}
        currentUser={currentUser}
      />
    </RealtimeProvider>
  )
}


export default AppLayout
