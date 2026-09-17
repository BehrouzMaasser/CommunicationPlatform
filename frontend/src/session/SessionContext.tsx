import {
  type ReactNode,
  useEffect,
  useState,
} from 'react'

import {
  ApiError,
} from '../api/client'
import {
  getCurrentUser,
} from '../api/session'
import type {
  CurrentUser,
} from '../types/users'

import {
  SessionContext,
  type AuthStatus,
} from './sessionContextState'


type SessionProviderProps = {
  children: ReactNode
}


export function SessionProvider({
  children,
}: SessionProviderProps) {
  const [
    currentUser,
    setCurrentUser,
  ] = useState<CurrentUser | null>(
    null,
  )

  const [
    authStatus,
    setAuthStatus,
  ] = useState<AuthStatus>(
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
          error instanceof ApiError
          && error.status === 401
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
    <SessionContext.Provider
      value={{
        authStatus,
        currentUser,
      }}
    >
      {children}
    </SessionContext.Provider>
  )
}
