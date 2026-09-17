import {
  createContext,
} from 'react'

import type {
  RealtimeClient,
} from './client'

import type {
  RealtimeStatus,
} from './types'


export type RealtimeContextValue = {
  client: RealtimeClient
  status: RealtimeStatus
  currentUserId?: number
  isUserOnline:
    (userId: number) => boolean
}


export const RealtimeContext =
  createContext<
    RealtimeContextValue | null
  >(null)
