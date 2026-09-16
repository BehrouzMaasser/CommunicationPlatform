import {
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
import VoiceRoomManagement from '../components/voice/VoiceRoomManagement'
import {
  getVoiceRoom,
  getVoiceRoomMembers,
  getVoiceRoomVoiceState,
  leaveVoiceRoomMembership,
  removeVoiceRoomMember,
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
    state: globalVoiceState,
    ownsCurrentParticipation,
    microphoneEnabled,
    error: voiceError,
    refresh: refreshGlobalVoice,
    joinVoiceRoom,
    leaveVoiceRoom,
    setMicrophoneEnabled,
    startAudioPlayback,
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


  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.member_added',
    handleRoomMembershipEvent,
  )

  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.member_removed',
    handleRoomMembershipEvent,
  )

  useRealtimeEvent<RoomVoiceEventPayload>(
    'voice_room.member_left',
    handleRoomMembershipEvent,
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
          <div>
            <h1 className="h2 mb-1">
              {room.name}
            </h1>

            <p className="text-secondary mb-0">
              Owned by @{room.owner.username}
            </p>
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

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center gap-3 mb-3">
            <h2 className="h5 mb-0">
              Voice
            </h2>

            {roomParticipants.length > 0 && (
              <span className="badge text-bg-success">
                {roomParticipants.length}{' '}
                in voice
              </span>
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

              <div className="d-flex flex-wrap gap-2">
                {roomParticipants.map(
                  (participation) => (
                    <span
                      className="badge rounded-pill text-bg-light border"
                      key={participation.id}
                    >
                      @{participation.user.username}
                      {participation.user.id ===
                        currentUserId
                        ? ' · you'
                        : ''}
                    </span>
                  ),
                )}
              </div>
            </div>
          )}

          <p className="small text-secondary mb-3">
            {mediaDescription}
          </p>

          {(actionError || voiceError) && (
            <div
              className="alert alert-danger py-2 px-3 small"
              role="alert"
            >
              {actionError ?? voiceError}
            </div>
          )}

          <div className="d-flex flex-wrap gap-2">
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
        </div>
      </div>

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
                      <div>
                        <div className="fw-semibold">
                          @{membership.user.username}
                        </div>

                        {membership.user.id ===
                          room.owner.id && (
                          <div className="small text-secondary">
                            Owner
                          </div>
                        )}
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
