import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { ApiError } from '../api/client'
import { getCurrentUser } from '../api/session'
import type { CurrentUser } from '../types/users'

type AuthStatus =
  | 'loading'
  | 'authenticated'
  | 'anonymous'
  | 'error'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `nav-link${isActive ? ' active' : ''}`

function AppLayout() {
  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null)

  const [authStatus, setAuthStatus] =
    useState<AuthStatus>('loading')

  useEffect(() => {
    let cancelled = false

    async function loadCurrentUser() {
      try {
        const user = await getCurrentUser()

        if (cancelled) {
          return
        }

        setCurrentUser(user)
        setAuthStatus('authenticated')
      } catch (error) {
        if (cancelled) {
          return
        }

        if (
          error instanceof ApiError &&
          error.status === 401
        ) {
          setCurrentUser(null)
          setAuthStatus('anonymous')
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
              className={navLinkClass}
              to="/friends"
            >
              Friends
            </NavLink>
            <NavLink
              className={navLinkClass}
              to="/messages"
            >
              Messages
            </NavLink>
            <NavLink
              className={navLinkClass}
              to="/groups"
            >
              Groups
            </NavLink>
          </div>

          <div className="ms-auto ps-3 text-white">
            {authStatus === 'loading' && (
              <span className="text-white-50">
                Checking session…
              </span>
            )}

            {authStatus === 'authenticated' &&
              currentUser && (
                <span>
                  Signed in as{' '}
                  <strong>
                    {currentUser.username}
                  </strong>
                </span>
              )}

            {authStatus === 'anonymous' && (
              <a
                className="btn btn-sm btn-outline-light"
                href="/accounts/login/"
              >
                Sign in
              </a>
            )}

            {authStatus === 'error' && (
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

export default AppLayout
