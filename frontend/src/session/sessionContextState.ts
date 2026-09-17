import {
  createContext,
} from 'react'

import type {
  CurrentUser,
} from '../types/users'


export type AuthStatus =
  | 'loading'
  | 'authenticated'
  | 'anonymous'
  | 'error'


export type SessionContextValue = {
  authStatus: AuthStatus
  currentUser: CurrentUser | null
}


export const SessionContext =
  createContext<SessionContextValue | null>(null)
