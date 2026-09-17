import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

import type {
  ReactNode,
} from 'react'

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
  RoomVoiceParticipantPayload,
} from '../realtime/voiceEvents'

import type {
  VoiceState,
} from '../types/voice'

import {
  getVoiceClientInstanceId,
} from './clientInstance'

import {
  voiceMediaClient,
  voiceMediaParticipantIdentity,
} from './client'

import {
  DEFAULT_VOICE_PARTICIPANT_VOLUME,
  normalizeVoiceParticipantVolume,
  readLastNonZeroVoiceParticipantVolume,
  readVoiceParticipantVolume,
  writeVoiceParticipantVolume,
} from './volumePreferences'

import {
  playVoiceRoomJoinSound,
  playVoiceRoomLeaveSound,
  primeVoiceRoomSounds,
} from './roomSounds'

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

  const [
    audioOutputMuted,
    setAudioOutputMutedState,
  ] =
    useState(false)

  const [error, setError] =
    useState<string | null>(
      null,
    )

  const [
    speakingParticipantIdentities,
    setSpeakingParticipantIdentities,
  ] = useState<string[]>([])

  const [
    audioPlaybackRequired,
    setAudioPlaybackRequired,
  ] = useState(false)

  const [
    participantVolumes,
    setParticipantVolumesState,
  ] = useState<Record<number, number>>(
    {},
  )

  const participantVolumesRef =
    useRef<Record<number, number>>(
      {},
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


  const hydrateParticipantVolumes =
    useCallback(
      (
        nextState: VoiceState,
      ): void => {
        let next =
          participantVolumesRef.current

        let changed = false

        for (
          const participation
          of nextState.participants
        ) {
          const userId =
            participation.user.id

          if (
            userId === currentUserId
            || next[userId] !== undefined
          ) {
            continue
          }

          if (!changed) {
            next = {
              ...next,
            }
            changed = true
          }

          next[userId] =
            readVoiceParticipantVolume(
              currentUserId ?? null,
              userId,
            )
        }

        if (!changed) {
          return
        }

        participantVolumesRef.current =
          next

        setParticipantVolumesState(
          next,
        )
      },
      [currentUserId],
    )


  const syncParticipantVolumesToMedia =
    useCallback(
      (
        nextState: VoiceState,
      ): void => {
        for (
          const participation
          of nextState.participants
        ) {
          const userId =
            participation.user.id

          if (userId === currentUserId) {
            continue
          }

          const volume =
            participantVolumesRef
              .current[userId]
            ??
            readVoiceParticipantVolume(
              currentUserId ?? null,
              userId,
            )

          voiceMediaClient
            .setParticipantVolume(
              participation.id,
              volume,
            )
        }
      },
      [currentUserId],
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

              voiceMediaClient
                .setOutputMuted(false)

              setAudioOutputMutedState(
                false,
              )

              continue
            }

            if (
              voiceMediaClient
                .isConnected
            ) {
              syncParticipantVolumesToMedia(
                desiredState,
              )

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

              syncParticipantVolumesToMedia(
                desiredState,
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
        syncParticipantVolumesToMedia,
      ],
    )


  const applyAuthoritativeState =
    useCallback(
      (
        nextState: VoiceState,
      ) => {
        desiredVoiceStateRef
          .current = nextState

        hydrateParticipantVolumes(
          nextState,
        )

        setState(nextState)

        setStatus('ready')

        setError(null)

        void reconcileMedia()
      },
      [
        hydrateParticipantVolumes,
        reconcileMedia,
      ],
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
        const currentState =
          desiredVoiceStateRef.current

        const alreadyJoinedHere =
          currentState.session?.kind ===
            'ROOM'
          &&
          currentState.session
            .status === 'ACTIVE'
          &&
          currentState.session
            .voice_room_id === roomId
          &&
          currentState
            .current_participation
            ?.client_instance_id ===
              clientInstanceId

        /*
         * Create/resume the Web Audio context
         * while we are still inside the user's
         * Join button gesture.
         */
        primeVoiceRoomSounds()

        await runStateMutation(
          () =>
            joinVoiceRoomRequest(
              roomId,
              clientInstanceId,
            ),
        )

        if (!alreadyJoinedHere) {
          playVoiceRoomJoinSound()
        }
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

          if (
            !nextEnabled
            && currentUserId !== undefined
          ) {
            const participation =
              desiredVoiceStateRef
                .current
                .participants
                .find(
                  (item) =>
                    item.user.id ===
                      currentUserId,
                )

            if (participation) {
              const identity =
                voiceMediaParticipantIdentity(
                  participation.id,
                )

              setSpeakingParticipantIdentities(
                (current) =>
                  current.filter(
                    (item) =>
                      item !== identity,
                  ),
              )
            }
          }

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
      [currentUserId],
    )


  const setAudioOutputMuted =
    useCallback(
      (
        muted: boolean,
      ): void => {
        voiceMediaClient
          .setOutputMuted(muted)

        setAudioOutputMutedState(
          muted,
        )
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


  const getParticipantVolume =
    useCallback(
      (
        userId: number,
      ): number => {
        return (
          participantVolumes[userId]
          ??
          DEFAULT_VOICE_PARTICIPANT_VOLUME
        )
      },
      [participantVolumes],
    )


  const setParticipantVolume =
    useCallback(
      (
        userId: number,
        value: number,
      ): void => {
        if (userId === currentUserId) {
          return
        }

        const volume =
          normalizeVoiceParticipantVolume(
            value,
          )

        const next = {
          ...participantVolumesRef.current,
          [userId]: volume,
        }

        participantVolumesRef.current =
          next

        setParticipantVolumesState(
          next,
        )

        writeVoiceParticipantVolume(
          currentUserId ?? null,
          userId,
          volume,
        )

        const participation =
          desiredVoiceStateRef
            .current
            .participants
            .find(
              (item) =>
                item.user.id === userId,
            )

        if (!participation) {
          return
        }

        voiceMediaClient
          .setParticipantVolume(
            participation.id,
            volume,
          )
      },
      [currentUserId],
    )


  const toggleParticipantMuted =
    useCallback(
      (
        userId: number,
      ): void => {
        if (userId === currentUserId) {
          return
        }

        const currentVolume =
          participantVolumesRef
            .current[userId]
          ??
          readVoiceParticipantVolume(
            currentUserId ?? null,
            userId,
          )

        const nextVolume =
          currentVolume > 0
            ? 0
            : readLastNonZeroVoiceParticipantVolume(
                currentUserId ?? null,
                userId,
              )

        setParticipantVolume(
          userId,
          nextVolume,
        )
      },
      [
        currentUserId,
        setParticipantVolume,
      ],
    )


  useEffect(
    () => {
      voiceMediaClient
        .setAudioPlaybackRequiredListener(
          setAudioPlaybackRequired,
        )

      return () => {
        voiceMediaClient
          .setAudioPlaybackRequiredListener(
            null,
          )

        setAudioPlaybackRequired(
          false,
        )
      }
    },
    [],
  )


  useEffect(
    () => {
      voiceMediaClient
        .setActiveSpeakersListener(
          (
            participantIdentities,
          ) => {
            setSpeakingParticipantIdentities(
              participantIdentities,
            )
          },
        )

      return () => {
        voiceMediaClient
          .setActiveSpeakersListener(
            null,
          )

        setSpeakingParticipantIdentities(
          [],
        )
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

      /*
       * Protect against a duplicated realtime
       * delivery producing the same cue twice.
       */
      const soundedEventIds =
        new Set<string>()

      function rememberSoundEvent(
        eventId: string,
      ): boolean {
        if (
          soundedEventIds.has(
            eventId,
          )
        ) {
          return false
        }

        soundedEventIds.add(
          eventId,
        )

        if (
          soundedEventIds.size > 100
        ) {
          const oldest =
            soundedEventIds
              .values()
              .next()
              .value

          if (oldest) {
            soundedEventIds.delete(
              oldest,
            )
          }
        }

        return true
      }

      const unsubscribe =
        VOICE_REALTIME_EVENT_TYPES
          .map(
            (eventType) =>
              realtimeClient.onEvent(
                eventType,
                (event) => {
                  const isRoomJoin =
                    eventType ===
                      'voice.room.participant_joined'

                  const isRoomLeave =
                    eventType ===
                      'voice.room.participant_left'
                    ||
                    eventType ===
                      'voice.room.participant_revoked'

                  if (
                    isRoomJoin
                    || isRoomLeave
                  ) {
                    const payload =
                      event.payload as RoomVoiceParticipantPayload

                    const currentState =
                      desiredVoiceStateRef
                        .current

                    /*
                     * Realtime events go to room
                     * members, not only people who
                     * are currently in voice.
                     *
                     * Only the tab/device that
                     * actually owns an active media
                     * participation should make a
                     * sound.
                     */
                    const ownsActiveRoomMedia =
                      currentState
                        .session
                        ?.kind === 'ROOM'
                      &&
                      currentState
                        .session
                        ?.status === 'ACTIVE'
                      &&
                      currentState
                        .session
                        ?.voice_room_id ===
                          payload.room_id
                      &&
                      currentState
                        .current_participation
                        ?.client_instance_id ===
                          clientInstanceId
                      &&
                      voiceMediaClient
                        .isConnected

                    /*
                     * Own joins are played explicitly
                     * after joinVoiceRoom succeeds.
                     * Own leaves/revocations should
                     * not play a goodbye sound on the
                     * client that is disappearing.
                     */
                    const isOwnEvent =
                      payload.user_id ===
                        currentUserId

                    if (
                      ownsActiveRoomMedia
                      && !isOwnEvent
                      && rememberSoundEvent(
                        event.event_id,
                      )
                    ) {
                      if (isRoomJoin) {
                        playVoiceRoomJoinSound()
                      } else {
                        playVoiceRoomLeaveSound()
                      }
                    }
                  }

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
      clientInstanceId,
      currentUserId,
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

        voiceMediaClient
          .setOutputMuted(false)

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

  const speakingIdentitySet =
    new Set(
      speakingParticipantIdentities,
    )

  const speakingUserIds =
    state.participants
      .filter(
        (participation) =>
          speakingIdentitySet.has(
            voiceMediaParticipantIdentity(
              participation.id,
            ),
          ),
      )
      .map(
        (participation) =>
          participation.user.id,
      )

  return (
    <VoiceContext.Provider
      value={{
        clientInstanceId,
        currentUserId:
          currentUserId ?? null,
        status,
        mediaStatus,
        audioPlaybackRequired,
        state,
        ownsCurrentParticipation,
        microphoneEnabled,
        audioOutputMuted,
        speakingUserIds,
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
        setAudioOutputMuted,
        startAudioPlayback,
        getParticipantVolume,
        setParticipantVolume,
        toggleParticipantMuted,
      }}
    >
      {children}
    </VoiceContext.Provider>
  )
}
