import {
  createContext,
} from 'react'

import type {
  VoiceState,
} from '../types/voice'


export type VoiceControllerStatus =
  | 'disabled'
  | 'loading'
  | 'ready'
  | 'unavailable'
  | 'error'


export type VoiceMediaStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error'


export type VoiceContextValue = {
  clientInstanceId: string
  currentUserId: number | null

  status: VoiceControllerStatus
  mediaStatus: VoiceMediaStatus

  state: VoiceState

  ownsCurrentParticipation: boolean
  microphoneEnabled: boolean

  error: string | null

  refresh: () => Promise<void>

  startDirectCall:
    (userId: number) => Promise<void>

  acceptDirectCall:
    (sessionId: string) => Promise<void>

  rejectDirectCall:
    (sessionId: string) => Promise<void>

  cancelDirectCall:
    (sessionId: string) => Promise<void>

  endDirectCall:
    (sessionId: string) => Promise<void>

  setMicrophoneEnabled:
    (enabled: boolean) => Promise<void>

  startAudioPlayback:
    () => Promise<void>
}


export const EMPTY_VOICE_STATE:
VoiceState = {
  session: null,
  current_participation: null,
  participants: [],
}


export const VoiceContext =
  createContext<
    VoiceContextValue | null
  >(null)
