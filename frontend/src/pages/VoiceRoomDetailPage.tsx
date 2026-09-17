import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Link,
  useNavigate,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import Avatar from '../components/users/Avatar'
import VoiceAudioSettings from '../components/voice/VoiceAudioSettings'
import VoiceRoomAvatar from '../components/voice/VoiceRoomAvatar'
import VoiceRoomManagement from '../components/voice/VoiceRoomManagement'
import {
  deleteVoiceRoom,
  getVoiceRoom,
  getVoiceRoomMembers,
  getVoiceRoomVoiceState,
  leaveVoiceRoomMembership,
  removeVoiceRoomAvatar,
  removeVoiceRoomMember,
  renameVoiceRoom,
  updateVoiceRoomAvatar,
} from '../api/voice'
import {
  useRealtimeEvent,
} from '../realtime/RealtimeContext'
import {
  useVoice,
} from '../voice/useVoice'

import type {
  VoiceRoom,
  VoiceRoomMembership,
  VoiceState,
} from '../types/voice'


type RoomVoiceEventPayload = {
  room_id: string
}


type RoomMemberEventPayload = {
  room_id: string
  user_id?: number
  member_user_id?: number
}


type PendingVoiceAction =
  | 'join'
  | 'leave'
  | 'microphone'
  | 'audio'
  | 'retry'
  | null


function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}


function VoiceRoomDetailPage() {
  const { roomId } = useParams()
  const navigate = useNavigate()

  const {
    currentUserId,
    status: voiceStatus,
    mediaStatus,
    audioPlaybackRequired,
    state: globalVoiceState,
    ownsCurrentParticipation,
    microphoneEnabled,
    speakingUserIds,
    error: voiceError,
    refresh: refreshGlobalVoice,
    joinVoiceRoom,
    leaveVoiceRoom,
    setMicrophoneEnabled,
    startAudioPlayback,
    getParticipantVolume,
    setParticipantVolume,
    toggleParticipantMuted,
  } = useVoice()

  const [room, setRoom] =
    useState<VoiceRoom | null>(null)

  const [members, setMembers] =
    useState<VoiceRoomMembership[]>([])

  const [
    roomVoiceState,
    setRoomVoiceState,
  ] =
    useState<VoiceState | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const [
    actionError,
    setActionError,
  ] =
    useState<string | null>(null)

  const [renameText, setRenameText] =
    useState('')
  const [avatarFile, setAvatarFile] =
    useState<File | null>(null)

  const [
    roomSettingsBusy,
    setRoomSettingsBusy,
  ] = useState<'rename' | 'delete' | 'avatar' | null>(
    null,
  )

  const [
    roomSettingsError,
    setRoomSettingsError,
  ] = useState<string | null>(null)

  const [
    roomSettingsNotice,
    setRoomSettingsNotice,
  ] = useState<string | null>(null)

  const [
    showDeleteConfirm,
    setShowDeleteConfirm,
  ] = useState(false)


  const [
    pendingMembershipAction,
    setPendingMembershipAction,
  ] = useState<string | null>(null)

  const [
    membershipError,
    setMembershipError,
  ] = useState<string | null>(null)


  const [
    pendingVoiceAction,
    setPendingVoiceAction,
  ] =
    useState<PendingVoiceAction>(
      null,
    )


  const refreshRoomVoice =
    useCallback(
      async () => {
        if (!roomId) {
          return
        }

        try {
          const nextState =
            await getVoiceRoomVoiceState(
              roomId,
            )

          setRoomVoiceState(
            nextState,
          )
        } catch {
          /*
           * The initial page load owns the
           * user-visible request error. A
           * transient realtime refresh should
           * not replace the whole page.
           */
        }
      },
      [roomId],
    )


  const refreshRoomMembershipState =
    useCallback(
      async () => {
        if (!roomId) {
          return
        }

        try {
          const [
            roomData,
            memberData,
          ] = await Promise.all([
            getVoiceRoom(roomId),
            getVoiceRoomMembers(roomId),
          ])

          setRoom(roomData)
          setRenameText(roomData.name)
          setMembers(memberData)
        } catch {
          /*
           * A transient realtime refresh should
           * not replace the current page state.
           */
        }
      },
      [roomId],
    )


  const handleRoomMembershipEvent =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomVoiceEventPayload
      }) => {
        if (
          payload.room_id === roomId
        ) {
          void refreshRoomMembershipState()
        }
      },
      [
        refreshRoomMembershipState,
        roomId,
      ],
    )


  const handleRoomVoiceEvent =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomVoiceEventPayload
      }) => {
        if (
          payload.room_id === roomId
        ) {
          void refreshRoomVoice()
        }
      },
      [
        refreshRoomVoice,
        roomId,
      ],
    )


  const handleRoomMemberRemoved =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomMemberEventPayload
      }) => {
        if (
          payload.room_id !== roomId
        ) {
          return
        }

        const removedUserId =
          payload.user_id
          ?? payload.member_user_id

        if (
          removedUserId ===
            currentUserId
        ) {
          /*
           * Membership is authoritative.
           * Once this account is removed,
           * it must immediately leave every
           * UI/media surface for this room.
           */
          void refreshGlobalVoice()

          navigate(
            '/voice',
            {
              replace: true,
            },
          )
          return
        }

        void refreshRoomMembershipState()
      },
      [
        currentUserId,
        navigate,
        refreshGlobalVoice,
        refreshRoomMembershipState,
        roomId,
      ],
    )


  const handleRoomRenamed =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomVoiceEventPayload
      }) => {
        if (
          payload.room_id === roomId
        ) {
          /*
           * The realtime event tells us that
           * the authoritative room changed.
           * Refetch instead of depending on
           * optional event payload fields.
           */
          void refreshRoomMembershipState()
        }
      },
      [
        refreshRoomMembershipState,
        roomId,
      ],
    )


  const handleRoomDeleted =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomVoiceEventPayload
      }) => {
        if (
          payload.room_id !== roomId
        ) {
          return
        }

        void refreshGlobalVoice()

        navigate(
          '/voice',
          {
            replace: true,
          },
        )
      },
      [
        navigate,
        refreshGlobalVoice,
        roomId,
      ],
    )


  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.member_added',
    handleRoomMembershipEvent,
  )

  useRealtimeEvent<RoomMemberEventPayload>(
    'voice_room.member_removed',
    handleRoomMemberRemoved,
  )

  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.member_left',
    handleRoomMembershipEvent,
  )


  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.renamed',
    handleRoomRenamed,
  )


  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.avatar_updated',
    handleRoomRenamed,
  )


  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.deleted',
    handleRoomDeleted,
  )


  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice.room.participant_joined',
    handleRoomVoiceEvent,
  )

  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice.room.participant_left',
    handleRoomVoiceEvent,
  )

  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice.room.participant_revoked',
    handleRoomVoiceEvent,
  )

  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice.room.session_ended',
    handleRoomVoiceEvent,
  )


  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!roomId) {
        setError(
          'Voice room ID is missing.',
        )
        setLoading(false)
        return
      }

      try {
        const [
          roomData,
          memberData,
          roomVoiceData,
        ] = await Promise.all([
          getVoiceRoom(roomId),
          getVoiceRoomMembers(roomId),
          getVoiceRoomVoiceState(
            roomId,
          ),
        ])

        if (!cancelled) {
          setRoom(roomData)
          setRenameText(roomData.name)
          setMembers(memberData)
          setRoomVoiceState(
            roomVoiceData,
          )
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(
            errorText(requestError),
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [roomId])


  async function handleAvatarUpload(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!roomId || !avatarFile || roomSettingsBusy !== null) {
      return
    }

    setRoomSettingsBusy('avatar')
    setRoomSettingsError(null)
    setRoomSettingsNotice(null)

    try {
      const updated = await updateVoiceRoomAvatar(
        roomId,
        avatarFile,
      )
      setRoom(updated)
      setAvatarFile(null)
      event.currentTarget.reset()
      setRoomSettingsNotice('Voice Room avatar updated.')
    } catch (requestError) {
      setRoomSettingsError(errorText(requestError))
    } finally {
      setRoomSettingsBusy(null)
    }
  }

  async function handleAvatarRemove() {
    if (!roomId || roomSettingsBusy !== null) {
      return
    }

    setRoomSettingsBusy('avatar')
    setRoomSettingsError(null)
    setRoomSettingsNotice(null)

    try {
      const updated = await removeVoiceRoomAvatar(roomId)
      setRoom(updated)
      setAvatarFile(null)
      setRoomSettingsNotice('Voice Room avatar removed.')
    } catch (requestError) {
      setRoomSettingsError(errorText(requestError))
    } finally {
      setRoomSettingsBusy(null)
    }
  }

  async function handleRenameRoom(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (
      !roomId
      || !room
      || roomSettingsBusy !== null
    ) {
      return
    }

    const name = renameText.trim()

    if (
      !name
      || name === room.name
    ) {
      return
    }

    setRoomSettingsBusy('rename')
    setRoomSettingsError(null)
    setRoomSettingsNotice(null)

    try {
      const updated =
        await renameVoiceRoom(
          roomId,
          name,
        )

      setRoom(updated)
      setRenameText(updated.name)
      setRoomSettingsNotice(
        'Voice Room renamed.',
      )
    } catch (requestError) {
      setRoomSettingsError(
        errorText(requestError),
      )
    } finally {
      setRoomSettingsBusy(null)
    }
  }


  async function handleDeleteRoom() {
    if (
      !roomId
      || roomSettingsBusy !== null
    ) {
      return
    }

    setRoomSettingsBusy('delete')
    setRoomSettingsError(null)
    setRoomSettingsNotice(null)

    try {
      await deleteVoiceRoom(roomId)

      setShowDeleteConfirm(false)

      /*
       * The backend ends any active room
       * session. Reconcile this client
       * immediately rather than waiting
       * solely for realtime delivery.
       */
      await refreshGlobalVoice()

      navigate(
        '/voice',
        {
          replace: true,
        },
      )
    } catch (requestError) {
      setRoomSettingsError(
        errorText(requestError),
      )
      setShowDeleteConfirm(false)
    } finally {
      setRoomSettingsBusy(null)
    }
  }


  async function handleRemoveMember(
    userId: number,
  ) {
    if (!roomId || pendingMembershipAction !== null) {
      return
    }

    const key = `remove-${userId}`

    setPendingMembershipAction(key)
    setMembershipError(null)

    try {
      await removeVoiceRoomMember(
        roomId,
        userId,
      )

      await refreshRoomMembershipState()
    } catch (requestError) {
      setMembershipError(
        errorText(requestError),
      )
    } finally {
      setPendingMembershipAction(null)
    }
  }


  async function handleLeaveRoom() {
    if (!roomId || pendingMembershipAction !== null) {
      return
    }

    setPendingMembershipAction('leave-room')
    setMembershipError(null)

    try {
      await leaveVoiceRoomMembership(
        roomId,
      )

      navigate('/voice')
    } catch (requestError) {
      setMembershipError(
        errorText(requestError),
      )
      setPendingMembershipAction(null)
    }
  }


  async function runVoiceAction(
    action: PendingVoiceAction,
    operation: () => Promise<void>,
  ) {
    if (
      action === null
      || pendingVoiceAction !== null
    ) {
      return
    }

    setPendingVoiceAction(action)
    setActionError(null)

    try {
      await operation()
      await refreshRoomVoice()
    } catch (requestError) {
      setActionError(
        errorText(requestError),
      )
    } finally {
      setPendingVoiceAction(null)
    }
  }


  if (loading) {
    return (
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading voice room"
        />
      </div>
    )
  }


  if (error || !room) {
    return (
      <section>
        <Link
          className="btn btn-sm btn-outline-secondary mb-3"
          to="/voice"
        >
          ← Voice rooms
        </Link>

        <div
          className="alert alert-danger"
          role="alert"
        >
          {error ?? 'Voice room not found.'}
        </div>
      </section>
    )
  }


  const accountSession =
    globalVoiceState.session

  const hasOpenAccountVoice =
    accountSession !== null
    && (
      accountSession.status ===
        'RINGING'
      ||
      accountSession.status ===
        'ACTIVE'
    )

  const isThisRoomSession =
    accountSession?.kind === 'ROOM'
    &&
    accountSession.voice_room_id ===
      room.id
    &&
    accountSession.status ===
      'ACTIVE'

  const ownsThisRoomSession =
    isThisRoomSession
    && ownsCurrentParticipation

  const activeOnAnotherClient =
    isThisRoomSession
    && !ownsCurrentParticipation

  const busyInOtherVoice =
    hasOpenAccountVoice
    && !isThisRoomSession

  const roomParticipants =
    roomVoiceState?.session?.status ===
      'ACTIVE'
      ? roomVoiceState.participants
      : []

  let mediaDescription =
    'Ready to join.'

  if (
    voiceStatus === 'loading'
  ) {
    mediaDescription =
      'Loading voice state…'
  } else if (
    voiceStatus === 'disabled'
    ||
    voiceStatus === 'unavailable'
  ) {
    mediaDescription =
      'Voice communication is unavailable.'
  } else if (
    voiceStatus === 'error'
  ) {
    mediaDescription =
      'Voice state could not be loaded.'
  } else if (
    busyInOtherVoice
  ) {
    mediaDescription =
      'Finish your current voice session first.'
  } else if (
    activeOnAnotherClient
  ) {
    mediaDescription =
      'You joined this room on another tab or device.'
  } else if (
    ownsThisRoomSession
  ) {
    mediaDescription = {
      disconnected:
        'Preparing audio…',
      connecting:
        'Connecting audio…',
      connected:
        microphoneEnabled
          ? 'Audio connected'
          : 'Audio connected · microphone muted',
      error:
        'Audio connection failed.',
    }[mediaStatus]
  }


  return (
    <section>
      <div className="mb-4">
        <Link
          className="btn btn-sm btn-outline-secondary mb-3"
          to="/voice"
        >
          ← Voice rooms
        </Link>

        <div className="d-flex flex-column flex-md-row justify-content-between gap-3">
          <div className="d-flex align-items-center gap-3">
            <VoiceRoomAvatar
              name={room.name}
              avatarUrl={room.avatar_url}
              size="lg"
            />
            <div>
              <h1 className="h2 mb-1">
                {room.name}
              </h1>

              <p className="text-secondary mb-0">
                Owned by @{room.owner.username}
              </p>
            </div>
          </div>

          <div className="align-self-md-start d-flex align-items-center gap-2">
            <span className="badge text-bg-secondary">
              {room.member_count}{' '}
              {room.member_count === 1
                ? 'member'
                : 'members'}
            </span>

            {currentUserId !== room.owner.id && (
              <button
                className="btn btn-sm btn-outline-danger"
                type="button"
                disabled={
                  pendingMembershipAction !== null
                }
                onClick={() =>
                  void handleLeaveRoom()
                }
              >
                {pendingMembershipAction ===
                'leave-room'
                  ? 'Leaving…'
                  : 'Leave room'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="card shadow-sm mb-4 voice-panel">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center gap-3 mb-3">
            <h2 className="h5 mb-0">
              Voice
            </h2>

            {roomParticipants.length > 0 && (
              <span className="badge voice-active-badge">
                {roomParticipants.length}{' '}
                in voice
              </span>
            )}
          </div>

          <div className="voice-room-control-bar d-flex flex-wrap align-items-center gap-2">
            {!isThisRoomSession && (
              <button
                className="btn btn-primary"
                type="button"
                disabled={
                  pendingVoiceAction !== null
                  || voiceStatus !== 'ready'
                  || busyInOtherVoice
                }
                onClick={() => {
                  void runVoiceAction(
                    'join',
                    () =>
                      joinVoiceRoom(
                        room.id,
                      ),
                  )
                }}
              >
                {pendingVoiceAction ===
                'join'
                  ? 'Joining…'
                  : 'Join voice'}
              </button>
            )}

            <VoiceAudioSettings buttonSize="md" />

            {ownsThisRoomSession && (
              <>
                {mediaStatus ===
                  'connected' && (
                  <>
                    <button
                      className="btn btn-outline-secondary"
                      type="button"
                      disabled={
                        pendingVoiceAction !==
                          null
                      }
                      onClick={() => {
                        void runVoiceAction(
                          'microphone',
                          () =>
                            setMicrophoneEnabled(
                              !microphoneEnabled,
                            ),
                        )
                      }}
                    >
                      {pendingVoiceAction ===
                      'microphone'
                        ? 'Updating…'
                        : microphoneEnabled
                          ? 'Mute'
                          : 'Unmute'}
                    </button>

                    {audioPlaybackRequired && (
                      <button
                        className="btn btn-outline-secondary"
                        type="button"
                        disabled={
                          pendingVoiceAction !==
                            null
                        }
                        onClick={() => {
                          void runVoiceAction(
                            'audio',
                            startAudioPlayback,
                          )
                        }}
                      >
                        {pendingVoiceAction ===
                        'audio'
                          ? 'Starting audio…'
                          : 'Enable audio'}
                      </button>
                    )}
                  </>
                )}

                {mediaStatus === 'error' && (
                  <button
                    className="btn btn-outline-primary"
                    type="button"
                    disabled={
                      pendingVoiceAction !==
                        null
                    }
                    onClick={() => {
                      void runVoiceAction(
                        'retry',
                        refreshGlobalVoice,
                      )
                    }}
                  >
                    {pendingVoiceAction ===
                    'retry'
                      ? 'Retrying…'
                      : 'Retry audio'}
                  </button>
                )}

                <button
                  className="btn btn-danger"
                  type="button"
                  disabled={
                    pendingVoiceAction !==
                      null
                  }
                  onClick={() => {
                    void runVoiceAction(
                      'leave',
                      () =>
                        leaveVoiceRoom(
                          room.id,
                        ),
                    )
                  }}
                >
                  {pendingVoiceAction ===
                  'leave'
                    ? 'Leaving…'
                    : 'Leave voice'}
                </button>
              </>
            )}

            {activeOnAnotherClient && (
              <button
                className="btn btn-secondary"
                type="button"
                disabled
              >
                Active elsewhere
              </button>
            )}
          </div>

          {roomParticipants.length === 0 ? (
            <p className="text-secondary">
              Nobody is connected.
            </p>
          ) : (
            <div className="mb-3">
              <div className="small text-secondary mb-2">
                Connected
              </div>

              <div className="d-flex flex-column gap-2">
                {roomParticipants.map(
                  (participation) => {
                    const isCurrentUser =
                      participation.user.id ===
                        currentUserId

                    const volumePercent =
                      Math.round(
                        getParticipantVolume(
                          participation.user.id,
                        ) * 100,
                      )

                    const isSpeaking =
                      speakingUserIds.includes(
                        participation.user.id,
                      )
                      && (
                        !isCurrentUser
                        || microphoneEnabled
                      )

                    return (
                      <div
                        className={
                          `voice-participant-row d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-2${
                            isSpeaking
                              ? ' voice-participant-row-speaking'
                              : ''
                          }`
                        }
                        key={participation.id}
                      >
                        <div className="voice-participant-identity">
                          <Avatar
                            user={participation.user}
                            size="sm"
                            alt=""
                          />

                          <div className="min-width-0">
                            <div className="fw-semibold text-truncate">
                              @{participation.user.username}
                              {isCurrentUser
                                ? ' · you'
                                : ''}
                            </div>

                            <span
                              className={`voice-participant-state${isSpeaking ? '' : ' invisible'}`}
                              aria-hidden={!isSpeaking}
                            >
                              Speaking
                            </span>
                          </div>
                        </div>

                        {!isCurrentUser
                          && ownsThisRoomSession
                          && mediaStatus ===
                            'connected' && (
                          <div
                            className="d-flex align-items-center gap-2"
                            style={{
                              minWidth: '14rem',
                            }}
                          >
                            <span
                              className="small text-secondary"
                              style={{
                                minWidth: '3rem',
                              }}
                            >
                              {volumePercent}%
                            </span>

                            <input
                              className="form-range m-0"
                              type="range"
                              min="0"
                              max="100"
                              step="5"
                              value={volumePercent}
                              aria-label={
                                `Volume for @${participation.user.username}`
                              }
                              onChange={(event) =>
                                setParticipantVolume(
                                  participation
                                    .user.id,
                                  Number(
                                    event.target
                                      .value,
                                  ) / 100,
                                )
                              }
                            />

                            <button
                              className="btn btn-sm btn-outline-secondary flex-shrink-0"
                              type="button"
                              onClick={() =>
                                toggleParticipantMuted(
                                  participation
                                    .user.id,
                                )
                              }
                            >
                              {volumePercent === 0
                                ? 'Unmute'
                                : 'Mute'}
                            </button>
                          </div>
                        )}
                      </div>
                    )
                  },
                )}
              </div>
            </div>
          )}

          <div className="voice-media-copy mb-3">
            <span>{mediaDescription}</span>
          </div>

          {(actionError || voiceError) && (
            <div
              className="alert alert-danger py-2 px-3 small"
              role="alert"
            >
              {actionError ?? voiceError}
            </div>
          )}

        </div>
      </div>

      {currentUserId === room.owner.id && (
        <div className="card shadow-sm mb-4">
          <div className="card-body">
            <h2 className="h5">
              Room settings
            </h2>

            {roomSettingsError && (
              <div className="alert alert-danger">
                {roomSettingsError}
              </div>
            )}

            {roomSettingsNotice && (
              <div className="alert alert-success">
                {roomSettingsNotice}
              </div>
            )}

            <div className="d-flex align-items-center gap-3 mb-4">
              <VoiceRoomAvatar
                name={room.name}
                avatarUrl={room.avatar_url}
                size="lg"
              />

              <div className="flex-grow-1">
                <form
                  className="d-flex flex-column flex-sm-row gap-2"
                  onSubmit={handleAvatarUpload}
                >
                  <input
                    className="form-control form-control-sm"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    disabled={roomSettingsBusy !== null}
                    onChange={(event) =>
                      setAvatarFile(
                        event.target.files?.[0] ?? null,
                      )
                    }
                    aria-label="Voice Room avatar"
                  />
                  <button
                    className="btn btn-sm btn-outline-primary"
                    type="submit"
                    disabled={
                      roomSettingsBusy !== null || !avatarFile
                    }
                  >
                    {roomSettingsBusy === 'avatar'
                      ? 'Saving…'
                      : 'Upload avatar'}
                  </button>
                  {room.avatar_url && (
                    <button
                      className="btn btn-sm btn-outline-secondary"
                      type="button"
                      disabled={roomSettingsBusy !== null}
                      onClick={() =>
                        void handleAvatarRemove()
                      }
                    >
                      Remove
                    </button>
                  )}
                </form>
                <div className="form-text">
                  JPEG, PNG or WebP. The image is cropped square.
                </div>
              </div>
            </div>

                        <form
              className="d-flex flex-column flex-sm-row gap-2 mb-4"
              onSubmit={handleRenameRoom}
            >
              <input
                className="form-control"
                type="text"
                maxLength={50}
                value={renameText}
                disabled={
                  roomSettingsBusy !== null
                }
                onChange={(event) =>
                  setRenameText(
                    event.target.value,
                  )
                }
                aria-label="Voice Room name"
              />

              <button
                className="btn btn-primary"
                type="submit"
                disabled={
                  roomSettingsBusy !== null
                  || !renameText.trim()
                  || renameText.trim() ===
                    room.name
                }
              >
                {roomSettingsBusy ===
                'rename'
                  ? 'Renaming…'
                  : 'Rename'}
              </button>
            </form>

            <hr />

            <h3 className="h6 text-danger">
              Delete Voice Room
            </h3>

            <p className="small text-secondary">
              This removes the room for all members
              and ends its active voice session.
            </p>

            {!showDeleteConfirm ? (
              <button
                className="btn btn-outline-danger"
                type="button"
                disabled={
                  roomSettingsBusy !== null
                }
                onClick={() =>
                  setShowDeleteConfirm(true)
                }
              >
                Delete room
              </button>
            ) : (
              <div className="border border-danger rounded p-3">
                <p className="mb-3">
                  Delete <strong>{room.name}</strong>?
                  This cannot be undone.
                </p>

                <div className="d-flex flex-wrap gap-2">
                  <button
                    className="btn btn-secondary"
                    type="button"
                    disabled={
                      roomSettingsBusy !== null
                    }
                    onClick={() =>
                      setShowDeleteConfirm(false)
                    }
                  >
                    Cancel
                  </button>

                  <button
                    className="btn btn-danger"
                    type="button"
                    disabled={
                      roomSettingsBusy !== null
                    }
                    onClick={() =>
                      void handleDeleteRoom()
                    }
                  >
                    {roomSettingsBusy ===
                    'delete'
                      ? 'Deleting…'
                      : 'Delete permanently'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {currentUserId === room.owner.id && (
        <VoiceRoomManagement
          room={room}
          members={members}
        />
      )}

      {membershipError && (
        <div className="alert alert-danger">
          {membershipError}
        </div>
      )}

      <div className="card shadow-sm">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h2 className="h5 mb-0">
              Members
            </h2>

            <span className="badge text-bg-secondary">
              {members.length}
            </span>
          </div>

          {members.length === 0 ? (
            <p className="text-secondary mb-0">
              No members found.
            </p>
          ) : (
            <div className="list-group">
              {members.map(
                (membership) => (
                  <div
                    className="list-group-item"
                    key={membership.id}
                  >
                    <div className="d-flex justify-content-between align-items-center gap-3">
                      <div className="directory-user-identity">
                        <Avatar
                          user={membership.user}
                          size="sm"
                          alt=""
                        />

                        <span className="directory-user-copy">
                          <span className="directory-user-name">
                            @{membership.user.username}
                          </span>

                          {membership.user.id ===
                            room.owner.id && (
                            <span className="directory-user-state">
                              Owner
                            </span>
                          )}
                        </span>
                      </div>

                      {currentUserId ===
                        room.owner.id
                        &&
                        membership.user.id !==
                          room.owner.id && (
                        <button
                          className="btn btn-sm btn-outline-danger"
                          type="button"
                          disabled={
                            pendingMembershipAction !==
                              null
                          }
                          onClick={() =>
                            void handleRemoveMember(
                              membership.user.id,
                            )
                          }
                        >
                          {pendingMembershipAction ===
                          `remove-${membership.user.id}`
                            ? 'Removing…'
                            : 'Remove'}
                        </button>
                      )}
                    </div>
                  </div>
                ),
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}


export default VoiceRoomDetailPage
