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
  browserAudioOutputPromptSupported,
  browserAudioOutputSelectionSupported,
  listBrowserAudioOutputDevices,
  requestBrowserAudioOutputDevice,
} from '../platform/browserAudioOutput'

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
} from '../realtime/useRealtime'

import {
  VOICE_REALTIME_EVENT_TYPES,
} from '../realtime/voiceEvents'

import type {
  RoomVoiceParticipantPayload,
} from '../realtime/voiceEvents'

import type {
  VoiceAudioOutputDevice,
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
  clearVoiceSessionMediaPreferences,
  normalizeVoiceOutputVolume,
  readVoiceNoiseGateThresholdDb,
  readVoiceOutputDeviceId,
  readVoiceOutputVolume,
  readVoiceSessionMediaPreferences,
  writeVoiceNoiseGateThresholdDb,
  writeVoiceOutputDeviceId,
  writeVoiceOutputVolume,
  writeVoiceSessionMediaPreferences,
} from './mediaPreferences'

import {
  normalizeVoiceNoiseGateThresholdDb,
  voiceNoiseGateSupported,
} from './noiseGateProcessor'

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
    microphoneNoiseGateThresholdDb,
    setMicrophoneNoiseGateThresholdDbState,
  ] = useState<number | null>(
    () =>
      readVoiceNoiseGateThresholdDb(
        currentUserId ?? null,
      ),
  )

  const [
    audioOutputMuted,
    setAudioOutputMutedState,
  ] =
    useState(false)

  const [
    audioOutputVolume,
    setAudioOutputVolumeState,
  ] = useState(
    () =>
      readVoiceOutputVolume(
        currentUserId ?? null,
      ),
  )

  const [
    audioOutputDeviceId,
    setAudioOutputDeviceIdState,
  ] = useState(
    () =>
      readVoiceOutputDeviceId(
        currentUserId ?? null,
      ),
  )

  const [
    audioOutputDevices,
    setAudioOutputDevices,
  ] = useState<VoiceAudioOutputDevice[]>([])

  const [error, setError] =
    useState<string | null>(
      null,
    )

  const [
    speakingParticipantIdentities,
    setSpeakingParticipantIdentities,
  ] = useState<string[]>([])

  const [
    mutedMicrophoneParticipantIdentities,
    setMutedMicrophoneParticipantIdentities,
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

  const audioOutputMutedRef =
    useRef(false)

  const microphoneNoiseGateThresholdDbRef =
    useRef(
      microphoneNoiseGateThresholdDb,
    )

  const audioOutputVolumeRef =
    useRef(audioOutputVolume)

  const audioOutputDeviceIdRef =
    useRef(audioOutputDeviceId)

  const activeOwnedSessionIdRef =
    useRef<string | null>(null)

  const mediaRetryTimerRef =
    useRef<number | null>(null)

  const mediaRetryAttemptRef =
    useRef(0)

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


  const clearMediaRetry =
    useCallback(
      (): void => {
        if (
          mediaRetryTimerRef.current
          !== null
        ) {
          window.clearTimeout(
            mediaRetryTimerRef.current,
          )

          mediaRetryTimerRef.current =
            null
        }

        mediaRetryAttemptRef.current = 0
      },
      [],
    )


  const persistActiveSessionMediaPreferences =
    useCallback(
      (
        overrides?: Partial<{
          microphoneEnabled: boolean
          audioOutputMuted: boolean
        }>,
      ): void => {
        const session =
          desiredVoiceStateRef
            .current.session

        const participation =
          desiredVoiceStateRef
            .current
            .current_participation

        if (
          currentUserId === undefined
          || session?.status !== 'ACTIVE'
          || participation
            ?.client_instance_id
            !== clientInstanceId
        ) {
          return
        }

        writeVoiceSessionMediaPreferences({
          currentUserId,
          sessionId: session.id,
          microphoneEnabled:
            overrides
              ?.microphoneEnabled
            ?? microphoneEnabled,
          audioOutputMuted:
            overrides
              ?.audioOutputMuted
            ?? audioOutputMutedRef.current,
        })
      },
      [
        clientInstanceId,
        currentUserId,
        microphoneEnabled,
      ],
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
              clearMediaRetry()

              const previousSessionId =
                activeOwnedSessionIdRef
                  .current

              if (previousSessionId) {
                clearVoiceSessionMediaPreferences(
                  currentUserId ?? null,
                  previousSessionId,
                )
              }

              activeOwnedSessionIdRef.current =
                null

              await voiceMediaClient
                .disconnect()

              setMediaStatus(
                'disconnected',
              )

              setMicrophoneEnabledState(
                false,
              )

              audioOutputMutedRef.current =
                false

              voiceMediaClient
                .setOutputMuted(false)

              setAudioOutputMutedState(
                false,
              )

              continue
            }

            activeOwnedSessionIdRef.current =
              session.id

            if (
              voiceMediaClient
                .isConnected
            ) {
              syncParticipantVolumesToMedia(
                desiredState,
              )

              clearMediaRetry()

              setMediaStatus(
                'connected',
              )

              continue
            }

            /*
             * LiveKit performs its own transient
             * reconnection while the Room object is
             * still alive. Do not race that recovery
             * with a second fresh Room connection.
             */
            if (
              voiceMediaClient
                .currentRoom !== null
            ) {
              setMediaStatus(
                'connecting',
              )

              continue
            }

            const recoveredPreferences =
              readVoiceSessionMediaPreferences(
                currentUserId ?? null,
                session.id,
              )

            const desiredMicrophoneEnabled =
              recoveredPreferences
                ?.microphoneEnabled
              ?? true

            const desiredOutputMuted =
              recoveredPreferences
                ?.audioOutputMuted
              ?? false

            audioOutputMutedRef.current =
              desiredOutputMuted

            voiceMediaClient
              .setOutputMuted(
                desiredOutputMuted,
              )

            voiceMediaClient
              .setOutputVolume(
                audioOutputVolumeRef
                  .current,
              )

            setAudioOutputMutedState(
              desiredOutputMuted,
            )

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

              const preferredOutputDeviceId =
                audioOutputDeviceIdRef
                  .current

              if (
                preferredOutputDeviceId
                && browserAudioOutputSelectionSupported()
              ) {
                try {
                  const switched =
                    await voiceMediaClient
                      .switchAudioOutputDevice(
                        preferredOutputDeviceId,
                      )

                  if (!switched) {
                    throw new Error(
                      'The preferred audio output is unavailable.',
                    )
                  }
                } catch {
                  audioOutputDeviceIdRef.current =
                    ''

                  setAudioOutputDeviceIdState(
                    '',
                  )

                  writeVoiceOutputDeviceId(
                    currentUserId ?? null,
                    '',
                  )
                }
              }

              await voiceMediaClient
                .setMicrophoneEnabled(
                  desiredMicrophoneEnabled,
                )

              setMicrophoneEnabledState(
                desiredMicrophoneEnabled,
              )

              if (
                currentUserId !== undefined
              ) {
                writeVoiceSessionMediaPreferences({
                  currentUserId,
                  sessionId: session.id,
                  microphoneEnabled:
                    desiredMicrophoneEnabled,
                  audioOutputMuted:
                    desiredOutputMuted,
                })
              }

              clearMediaRetry()

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

              const retryDelays = [
                1000,
                2000,
                5000,
                10000,
              ]

              const attempt =
                mediaRetryAttemptRef
                  .current

              const delay =
                retryDelays[
                  Math.min(
                    attempt,
                    retryDelays.length - 1,
                  )
                ]

              mediaRetryAttemptRef.current =
                attempt + 1

              if (
                mediaRetryTimerRef.current
                !== null
              ) {
                window.clearTimeout(
                  mediaRetryTimerRef.current,
                )
              }

              mediaRetryTimerRef.current =
                window.setTimeout(
                  () => {
                    mediaRetryTimerRef.current =
                      null

                    void reconcileMedia()
                  },
                  delay,
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
        clearMediaRetry,
        clientInstanceId,
        currentUserId,
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

          persistActiveSessionMediaPreferences({
            microphoneEnabled:
              nextEnabled,
          })

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
      [
        currentUserId,
        persistActiveSessionMediaPreferences,
      ],
    )


  const setMicrophoneNoiseGateThresholdDb =
    useCallback(
      async (
        value: number | null,
      ): Promise<void> => {
        const threshold =
          normalizeVoiceNoiseGateThresholdDb(
            value,
          )

        microphoneNoiseGateThresholdDbRef.current =
          threshold

        try {
          await voiceMediaClient
            .setMicrophoneNoiseGateThresholdDb(
              threshold,
            )

          setMicrophoneNoiseGateThresholdDbState(
            threshold,
          )

          writeVoiceNoiseGateThresholdDb(
            currentUserId ?? null,
            threshold,
          )

          setError(null)
        } catch (
          noiseGateError
        ) {
          setError(
            errorMessage(
              noiseGateError,
            ),
          )

          throw noiseGateError
        }
      },
      [currentUserId],
    )


  const setAudioOutputMuted =
    useCallback(
      (
        muted: boolean,
      ): void => {
        audioOutputMutedRef.current =
          muted

        voiceMediaClient
          .setOutputMuted(muted)

        setAudioOutputMutedState(
          muted,
        )

        persistActiveSessionMediaPreferences({
          audioOutputMuted: muted,
        })
      },
      [persistActiveSessionMediaPreferences],
    )


  const setAudioOutputVolume =
    useCallback(
      (
        value: number,
      ): void => {
        const volume =
          normalizeVoiceOutputVolume(
            value,
          )

        audioOutputVolumeRef.current =
          volume

        voiceMediaClient
          .setOutputVolume(volume)

        setAudioOutputVolumeState(
          volume,
        )

        writeVoiceOutputVolume(
          currentUserId ?? null,
          volume,
        )
      },
      [currentUserId],
    )


  const refreshAudioOutputDevices =
    useCallback(
      async (): Promise<void> => {
        if (
          !browserAudioOutputSelectionSupported()
        ) {
          setAudioOutputDevices([])
          return
        }

        const devices =
          await listBrowserAudioOutputDevices()

        setAudioOutputDevices(
          devices.map(
            (device) => ({
              device_id:
                device.deviceId,
              label: device.label,
            }),
          ),
        )
      },
      [],
    )


  const setAudioOutputDevice =
    useCallback(
      async (
        deviceId: string,
      ): Promise<void> => {
        if (
          !browserAudioOutputSelectionSupported()
        ) {
          throw new Error(
            'Audio output selection is not supported by this browser.',
          )
        }

        if (mediaStatus === 'connected') {
          const switched =
            await voiceMediaClient
              .switchAudioOutputDevice(
                deviceId,
              )

          if (!switched) {
            throw new Error(
              'Could not switch the audio output device.',
            )
          }
        }

        audioOutputDeviceIdRef.current =
          deviceId

        setAudioOutputDeviceIdState(
          deviceId,
        )

        writeVoiceOutputDeviceId(
          currentUserId ?? null,
          deviceId,
        )

        setError(null)
      },
      [
        currentUserId,
        mediaStatus,
      ],
    )


  const chooseAudioOutputDevice =
    useCallback(
      async (): Promise<void> => {
        const selected =
          await requestBrowserAudioOutputDevice(
            audioOutputDeviceIdRef
              .current || undefined,
          )

        await setAudioOutputDevice(
          selected.deviceId,
        )

        await refreshAudioOutputDevices()
      },
      [
        refreshAudioOutputDevices,
        setAudioOutputDevice,
      ],
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
        .setConnectionStatusListener(
          (connectionStatus) => {
            if (
              connectionStatus ===
                'connected'
            ) {
              clearMediaRetry()
              setMediaStatus(
                'connected',
              )
              setError(null)
              return
            }

            if (
              connectionStatus ===
                'connecting'
            ) {
              setMediaStatus(
                'connecting',
              )
              return
            }

            const currentState =
              desiredVoiceStateRef
                .current

            const stillOwnsActiveSession =
              enabled
              && currentState
                .session
                ?.status === 'ACTIVE'
              && currentState
                .current_participation
                ?.client_instance_id
                === clientInstanceId

            if (stillOwnsActiveSession) {
              setMediaStatus(
                'connecting',
              )

              if (
                mediaRetryTimerRef.current
                !== null
              ) {
                window.clearTimeout(
                  mediaRetryTimerRef.current,
                )
              }

              mediaRetryTimerRef.current =
                window.setTimeout(
                  () => {
                    mediaRetryTimerRef.current =
                      null

                    void reconcileMedia()
                  },
                  500,
                )
            } else {
              setMediaStatus(
                'disconnected',
              )
            }
          },
        )

      return () => {
        voiceMediaClient
          .setConnectionStatusListener(
            null,
          )
      }
    },
    [
      clearMediaRetry,
      clientInstanceId,
      enabled,
      reconcileMedia,
    ],
  )


  useEffect(
    () => {
      voiceMediaClient
        .setOutputVolume(
          audioOutputVolumeRef.current,
        )
    },
    [],
  )


  useEffect(
    () => {
      void voiceMediaClient
        .setMicrophoneNoiseGateThresholdDb(
          microphoneNoiseGateThresholdDbRef.current,
        )
        .catch(() => {
          /* The setting can be retried from the Audio panel. */
        })
    },
    [],
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
      voiceMediaClient
        .setMutedMicrophonesListener(
          (
            participantIdentities,
          ) => {
            setMutedMicrophoneParticipantIdentities(
              participantIdentities,
            )
          },
        )

      return () => {
        voiceMediaClient
          .setMutedMicrophonesListener(
            null,
          )

        setMutedMicrophoneParticipantIdentities(
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

      const recover = () => {
        const currentState =
          desiredVoiceStateRef.current

        if (
          currentState.session
            ?.status !== 'ACTIVE'
          || currentState
            .current_participation
            ?.client_instance_id
            !== clientInstanceId
        ) {
          return
        }

        if (
          document.visibilityState
            === 'visible'
          && navigator.onLine
        ) {
          void refresh()
        }
      }

      const handleVisibilityChange = () => {
        recover()
      }

      window.addEventListener(
        'online',
        recover,
      )

      document.addEventListener(
        'visibilitychange',
        handleVisibilityChange,
      )

      return () => {
        window.removeEventListener(
          'online',
          recover,
        )

        document.removeEventListener(
          'visibilitychange',
          handleVisibilityChange,
        )
      }
    },
    [
      clientInstanceId,
      enabled,
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

        if (
          mediaRetryTimerRef.current
          !== null
        ) {
          window.clearTimeout(
            mediaRetryTimerRef.current,
          )

          mediaRetryTimerRef.current =
            null
        }

        voiceMediaClient
          .setConnectionStatusListener(
            null,
          )

        voiceMediaClient
          .setMutedMicrophonesListener(
            null,
          )

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

  const mutedMicrophoneIdentitySet =
    new Set(
      mutedMicrophoneParticipantIdentities,
    )

  const mutedUserIds =
    state.participants
      .filter(
        (participation) => {
          if (
            participation.user.id
              === currentUserId
          ) {
            return (
              ownsCurrentParticipation
              && !microphoneEnabled
            )
          }

          return mutedMicrophoneIdentitySet.has(
            voiceMediaParticipantIdentity(
              participation.id,
            ),
          )
        },
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
        microphoneNoiseGateThresholdDb,
        microphoneNoiseGateSupported:
          voiceNoiseGateSupported(),
        audioOutputMuted,
        audioOutputVolume,
        audioOutputDeviceId,
        audioOutputDevices,
        audioOutputSelectionSupported:
          browserAudioOutputSelectionSupported(),
        audioOutputPromptSupported:
          browserAudioOutputPromptSupported(),
        speakingUserIds,
        mutedUserIds,
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
        setMicrophoneNoiseGateThresholdDb,
        setAudioOutputMuted,
        setAudioOutputVolume,
        refreshAudioOutputDevices,
        setAudioOutputDevice,
        chooseAudioOutputDevice,
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
