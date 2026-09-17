import {
  createContext,
} from 'react'

import type {
  VoiceAudioOutputDevice,
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
  audioPlaybackRequired: boolean

  state: VoiceState

  ownsCurrentParticipation: boolean
  microphoneEnabled: boolean
  audioOutputMuted: boolean
  audioOutputVolume: number
  audioOutputDeviceId: string
  audioOutputDevices:
    VoiceAudioOutputDevice[]
  audioOutputSelectionSupported: boolean
  audioOutputPromptSupported: boolean
  speakingUserIds: number[]

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

  joinVoiceRoom:
    (roomId: string) => Promise<void>

  leaveVoiceRoom:
    (roomId: string) => Promise<void>

  setMicrophoneEnabled:
    (enabled: boolean) => Promise<void>

  setAudioOutputMuted:
    (muted: boolean) => void

  setAudioOutputVolume:
    (volume: number) => void

  refreshAudioOutputDevices:
    () => Promise<void>

  setAudioOutputDevice:
    (deviceId: string) => Promise<void>

  chooseAudioOutputDevice:
    () => Promise<void>

  startAudioPlayback:
    () => Promise<void>

  getParticipantVolume:
    (userId: number) => number

  setParticipantVolume:
    (
      userId: number,
      volume: number,
    ) => void

  toggleParticipantMuted:
    (userId: number) => void
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
