import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

import type {
  ReactNode,
} from 'react'

import VoiceCallOverlay from '../components/voice/VoiceCallOverlay'
import VoiceRoomOverlay from '../components/voice/VoiceRoomOverlay'

import {
  ApiError,
} from '../api/client'

import {
  acceptDirectCall as acceptDirectCallRequest,
  cancelDirectCall as cancelDirectCallRequest,
  endDirectCall as endDirectCallRequest,
  getVoiceMediaCredentials,
  getVoiceState,
  joinVoiceRoom as joinVoiceRoomRequest,
  leaveVoiceRoom as leaveVoiceRoomRequest,
  rejectDirectCall as rejectDirectCallRequest,
  startDirectCall as startDirectCallRequest,
} from '../api/voice'

import {
  useRealtime,
} from '../realtime/RealtimeContext'

import {
  VOICE_REALTIME_EVENT_TYPES,
} from '../realtime/voiceEvents'

import type {
  VoiceState,
} from '../types/voice'

import {
  getVoiceClientInstanceId,
} from './clientInstance'

import {
  voiceMediaClient,
} from './client'

import {
  EMPTY_VOICE_STATE,
  VoiceContext,
} from './voiceContextState'

import type {
  VoiceControllerStatus,
  VoiceMediaStatus,
} from './voiceContextState'


type VoiceProviderProps = {
  children: ReactNode
  enabled: boolean
  currentUserId?: number
}


function errorMessage(
  error: unknown,
): string {
  if (error instanceof Error) {
    return error.message
  }

  return 'Voice communication failed.'
}


export function VoiceProvider({
  children,
  enabled,
  currentUserId,
}: VoiceProviderProps) {
  const { client: realtimeClient } =
    useRealtime()

  const [clientInstanceId] =
    useState(
      getVoiceClientInstanceId,
    )

  const [state, setState] =
    useState<VoiceState>(
      EMPTY_VOICE_STATE,
    )

  const [status, setStatus] =
    useState<VoiceControllerStatus>(
      enabled
        ? 'loading'
        : 'disabled',
    )

  const [
    mediaStatus,
    setMediaStatus,
  ] =
    useState<VoiceMediaStatus>(
      'disconnected',
    )

  const [
    microphoneEnabled,
    setMicrophoneEnabledState,
  ] =
    useState(false)

  const [error, setError] =
    useState<string | null>(
      null,
    )

  const desiredVoiceStateRef =
    useRef<VoiceState>(
      EMPTY_VOICE_STATE,
    )

  const mediaReconcileRunningRef =
    useRef(false)

  const mediaReconcileRequestedRef =
    useRef(false)

  const refreshPromiseRef =
    useRef<Promise<void> | null>(
      null,
    )


  const reconcileMedia =
    useCallback(
      async (): Promise<void> => {
        if (
          mediaReconcileRunningRef
            .current
        ) {
          mediaReconcileRequestedRef
            .current = true

          return
        }

        mediaReconcileRunningRef
          .current = true

        try {
          do {
            mediaReconcileRequestedRef
              .current = false

            const desiredState =
              desiredVoiceStateRef
                .current

            const session =
              desiredState.session

            const participation =
              desiredState
                .current_participation

            const ownsActiveSession =
              enabled
              &&
              session !== null
              &&
              session.status ===
                'ACTIVE'
              &&
              participation
                ?.client_instance_id
                === clientInstanceId

            if (!ownsActiveSession) {
              await voiceMediaClient
                .disconnect()

              setMediaStatus(
                'disconnected',
              )

              setMicrophoneEnabledState(
                false,
              )

              continue
            }

            if (
              voiceMediaClient
                .isConnected
            ) {
              setMediaStatus(
                'connected',
              )

              continue
            }

            setMediaStatus(
              'connecting',
            )

            try {
              const credentials =
                await (
                  getVoiceMediaCredentials(
                    session.id,
                    clientInstanceId,
                  )
                )

              await voiceMediaClient
                .connect(
                  credentials,
                )

              await voiceMediaClient
                .setMicrophoneEnabled(
                  true,
                )

              setMicrophoneEnabledState(
                true,
              )

              setMediaStatus(
                'connected',
              )

              setError(null)
            } catch (
              mediaError
            ) {
              await voiceMediaClient
                .disconnect()

              setMicrophoneEnabledState(
                false,
              )

              setMediaStatus(
                'error',
              )

              setError(
                errorMessage(
                  mediaError,
                ),
              )
            }
          } while (
            mediaReconcileRequestedRef
              .current
          )
        } finally {
          mediaReconcileRunningRef
            .current = false

          /*
           * A request can arrive between the final
           * loop condition and releasing the lock.
           */
          if (
            mediaReconcileRequestedRef
              .current
          ) {
            void reconcileMedia()
          }
        }
      },
      [
        clientInstanceId,
        enabled,
      ],
    )


  const applyAuthoritativeState =
    useCallback(
      (
        nextState: VoiceState,
      ) => {
        desiredVoiceStateRef
          .current = nextState

        setState(nextState)

        setStatus('ready')

        setError(null)

        void reconcileMedia()
      },
      [reconcileMedia],
    )


  const markVoiceUnavailable =
    useCallback(
      () => {
        desiredVoiceStateRef
          .current =
            EMPTY_VOICE_STATE

        setState(
          EMPTY_VOICE_STATE,
        )

        setStatus(
          'unavailable',
        )

        setError(null)

        void reconcileMedia()
      },
      [reconcileMedia],
    )


  const refresh =
    useCallback(
      async (): Promise<void> => {
        if (!enabled) {
          return
        }

        if (
          refreshPromiseRef.current
        ) {
          return (
            refreshPromiseRef.current
          )
        }

        setStatus(
          (currentStatus) =>
            currentStatus === 'ready'
              ? currentStatus
              : 'loading',
        )

        const operation =
          (async () => {
            try {
              const nextState =
                await getVoiceState()

              applyAuthoritativeState(
                nextState,
              )
            } catch (
              refreshError
            ) {
              if (
                refreshError
                  instanceof ApiError
                &&
                refreshError.status
                  === 503
              ) {
                markVoiceUnavailable()
                return
              }

              setStatus('error')

              setError(
                errorMessage(
                  refreshError,
                ),
              )
            }
          })()

        refreshPromiseRef.current =
          operation

        try {
          await operation
        } finally {
          if (
            refreshPromiseRef.current
            === operation
          ) {
            refreshPromiseRef.current =
              null
          }
        }
      },
      [
        applyAuthoritativeState,
        enabled,
        markVoiceUnavailable,
      ],
    )


  const runStateMutation =
    useCallback(
      async (
        operation:
          () => Promise<VoiceState>,
      ): Promise<void> => {
        try {
          const nextState =
            await operation()

          applyAuthoritativeState(
            nextState,
          )
        } catch (
          mutationError
        ) {
          if (
            mutationError
              instanceof ApiError
            &&
            mutationError.status
              === 503
          ) {
            markVoiceUnavailable()
          } else {
            setError(
              errorMessage(
                mutationError,
              ),
            )
          }

          throw mutationError
        }
      },
      [
        applyAuthoritativeState,
        markVoiceUnavailable,
      ],
    )


  const startDirectCall =
    useCallback(
      async (
        userId: number,
      ): Promise<void> => {
        await runStateMutation(
          () =>
            startDirectCallRequest(
              userId,
              clientInstanceId,
            ),
        )
      },
      [
        clientInstanceId,
        runStateMutation,
      ],
    )


  const acceptDirectCall =
    useCallback(
      async (
        sessionId: string,
      ): Promise<void> => {
        await runStateMutation(
          () =>
            acceptDirectCallRequest(
              sessionId,
              clientInstanceId,
            ),
        )
      },
      [
        clientInstanceId,
        runStateMutation,
      ],
    )


  const rejectDirectCall =
    useCallback(
      async (
        sessionId: string,
      ): Promise<void> => {
        await runStateMutation(
          () =>
            rejectDirectCallRequest(
              sessionId,
            ),
        )
      },
      [runStateMutation],
    )


  const cancelDirectCall =
    useCallback(
      async (
        sessionId: string,
      ): Promise<void> => {
        await runStateMutation(
          () =>
            cancelDirectCallRequest(
              sessionId,
            ),
        )
      },
      [runStateMutation],
    )


  const endDirectCall =
    useCallback(
      async (
        sessionId: string,
      ): Promise<void> => {
        await runStateMutation(
          () =>
            endDirectCallRequest(
              sessionId,
            ),
        )
      },
      [runStateMutation],
    )


  const joinVoiceRoom =
    useCallback(
      async (
        roomId: string,
      ): Promise<void> => {
        await runStateMutation(
          () =>
            joinVoiceRoomRequest(
              roomId,
              clientInstanceId,
            ),
        )
      },
      [
        clientInstanceId,
        runStateMutation,
      ],
    )


  const leaveVoiceRoom =
    useCallback(
      async (
        roomId: string,
      ): Promise<void> => {
        await runStateMutation(
          async () => {
            await leaveVoiceRoomRequest(
              roomId,
              clientInstanceId,
            )

            /*
             * The leave endpoint is room-scoped.
             * Re-read the account-scoped state so
             * VoiceContext cannot retain somebody
             * else's still-active room session.
             */
            return getVoiceState()
          },
        )
      },
      [
        clientInstanceId,
        runStateMutation,
      ],
    )


  const setMicrophoneEnabled =
    useCallback(
      async (
        nextEnabled: boolean,
      ): Promise<void> => {
        try {
          await voiceMediaClient
            .setMicrophoneEnabled(
              nextEnabled,
            )

          setMicrophoneEnabledState(
            nextEnabled,
          )

          setError(null)
        } catch (
          microphoneError
        ) {
          setError(
            errorMessage(
              microphoneError,
            ),
          )

          throw microphoneError
        }
      },
      [],
    )


  const startAudioPlayback =
    useCallback(
      async (): Promise<void> => {
        try {
          await voiceMediaClient
            .startAudioPlayback()

          setError(null)
        } catch (
          playbackError
        ) {
          setError(
            errorMessage(
              playbackError,
            ),
          )

          throw playbackError
        }
      },
      [],
    )


  useEffect(
    () => {
      if (!enabled) {
        desiredVoiceStateRef
          .current =
            EMPTY_VOICE_STATE

        void reconcileMedia()

        return
      }

      void refresh()
    },
    [
      enabled,
      reconcileMedia,
      refresh,
    ],
  )


  useEffect(
    () => {
      if (!enabled) {
        return
      }

      const unsubscribe =
        VOICE_REALTIME_EVENT_TYPES
          .map(
            (eventType) =>
              realtimeClient.onEvent(
                eventType,
                () => {
                  void refresh()
                },
              ),
          )

      return () => {
        for (
          const stopListening
          of unsubscribe
        ) {
          stopListening()
        }
      }
    },
    [
      enabled,
      realtimeClient,
      refresh,
    ],
  )


  useEffect(
    () => {
      return () => {
        desiredVoiceStateRef
          .current =
            EMPTY_VOICE_STATE

        void voiceMediaClient
          .disconnect()
      }
    },
    [],
  )


  const ownsCurrentParticipation =
    state.current_participation
      ?.client_instance_id
      === clientInstanceId

  return (
    <VoiceContext.Provider
      value={{
        clientInstanceId,
        currentUserId:
          currentUserId ?? null,
        status,
        mediaStatus,
        state,
        ownsCurrentParticipation,
        microphoneEnabled,
        error,
        refresh,
        startDirectCall,
        acceptDirectCall,
        rejectDirectCall,
        cancelDirectCall,
        endDirectCall,
        joinVoiceRoom,
        leaveVoiceRoom,
        setMicrophoneEnabled,
        startAudioPlayback,
      }}
    >
      {children}
      <VoiceCallOverlay />
      <VoiceRoomOverlay
        key={
          state.session?.kind === 'ROOM'
            ? state.session.id
            : 'voice-room-idle'
        }
      />
    </VoiceContext.Provider>
  )
}
