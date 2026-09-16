import {
  useCallback,
  useEffect,
  useState,
} from 'react'

import {
  Link,
} from 'react-router-dom'

import {
  ApiError,
} from '../../api/client'

import {
  getVoiceRoom,
} from '../../api/voice'

import {
  useRealtimeEvent,
} from '../../realtime/RealtimeContext'

import type {
  VoiceRoom,
} from '../../types/voice'

import {
  useVoice,
} from '../../voice/useVoice'


type PendingAction =
  | 'microphone'
  | 'audio'
  | 'retry'
  | 'leave'
  | null


type RoomEventPayload = {
  room_id: string
}


function describeError(
  error: unknown,
): string {
  if (error instanceof Error) {
    return error.message
  }

  return 'The voice action failed.'
}


function VoiceRoomOverlay() {
  const {
    currentUserId,
    state,
    mediaStatus,
    ownsCurrentParticipation,
    microphoneEnabled,
    speakingUserIds,
    error,
    leaveVoiceRoom,
    setMicrophoneEnabled,
    startAudioPlayback,
    refresh,
  } = useVoice()

  const [
    room,
    setRoom,
  ] = useState<VoiceRoom | null>(
    null,
  )

  const [
    roomError,
    setRoomError,
  ] = useState<string | null>(
    null,
  )

  const [
    pendingAction,
    setPendingAction,
  ] = useState<PendingAction>(
    null,
  )

  const [
    localError,
    setLocalError,
  ] = useState<string | null>(
    null,
  )

  const session = state.session

  const roomId =
    session?.voice_room_id ?? null

  const isActiveRoomSession =
    session !== null
    && session.kind === 'ROOM'
    && session.status === 'ACTIVE'
    && roomId !== null


  const refreshRoom =
    useCallback(
      async (
        targetRoomId: string,
      ): Promise<void> => {
        try {
          const nextRoom =
            await getVoiceRoom(
              targetRoomId,
            )

          setRoom(nextRoom)
          setRoomError(null)
        } catch (requestError) {
          /*
           * A membership revocation or room
           * deletion can race this request.
           * Reconcile the account voice state
           * rather than retaining stale UI.
           */
          if (
            requestError instanceof ApiError
            && requestError.status === 404
          ) {
            setRoom(null)
            void refresh()
            return
          }

          setRoomError(
            describeError(
              requestError,
            ),
          )
        }
      },
      [
        refresh,
      ],
    )


  useEffect(
    () => {
      if (
        !isActiveRoomSession
        || !roomId
      ) {
        return
      }

      let cancelled = false

      void getVoiceRoom(roomId)
        .then((nextRoom) => {
          if (cancelled) {
            return
          }

          setRoom(nextRoom)
          setRoomError(null)
        })
        .catch((requestError) => {
          if (cancelled) {
            return
          }

          if (
            requestError instanceof ApiError
            && requestError.status === 404
          ) {
            setRoom(null)
            void refresh()
            return
          }

          setRoomError(
            describeError(
              requestError,
            ),
          )
        })

      return () => {
        cancelled = true
      }
    },
    [
      isActiveRoomSession,
      refresh,
      roomId,
    ],
  )


  const handleRoomRenamed =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomEventPayload
      }) => {
        if (
          payload.room_id === roomId
        ) {
          void refreshRoom(
            payload.room_id,
          )
        }
      },
      [
        refreshRoom,
        roomId,
      ],
    )


  useRealtimeEvent<RoomEventPayload>(
    'voice_room.renamed',
    handleRoomRenamed,
  )


  if (
    !isActiveRoomSession
    || !session
    || !roomId
  ) {
    return null
  }


  const busy =
    pendingAction !== null


  async function runAction(
    action: PendingAction,
    operation:
      () => Promise<void>,
  ) {
    if (!action || busy) {
      return
    }

    setPendingAction(action)
    setLocalError(null)

    try {
      await operation()
    } catch (actionError) {
      setLocalError(
        describeError(
          actionError,
        ),
      )
    } finally {
      setPendingAction(null)
    }
  }


  let statusText: string

  if (!ownsCurrentParticipation) {
    statusText =
      'Voice active on another tab or device'
  } else {
    statusText = {
      disconnected:
        'Preparing audio…',
      connecting:
        'Connecting audio…',
      connected:
        microphoneEnabled
          ? 'Connected'
          : 'Connected · microphone muted',
      error:
        'Audio connection failed',
    }[mediaStatus]
  }


  const roomName =
    room?.name ?? 'Voice Room'

  const connectedCount =
    state.participants.length

  const speakingParticipants =
    state.participants.filter(
      (participation) =>
        speakingUserIds.includes(
          participation.user.id,
        )
        && (
          participation.user.id !==
            currentUserId
          || microphoneEnabled
        ),
    )


  return (
    <div
      className="position-fixed bottom-0 start-50 translate-middle-x p-3 w-100"
      style={{
        maxWidth: '38rem',
        zIndex: 1075,
      }}
      aria-live="polite"
    >
      <div className="card shadow-lg border-success">
        <div className="card-body">
          <div className="d-flex align-items-start justify-content-between gap-3">
            <div className="min-w-0">
              <div className="d-flex align-items-center flex-wrap gap-2">
                <Link
                  className="fw-semibold text-decoration-none text-truncate"
                  to={`/voice/rooms/${roomId}`}
                >
                  {roomName}
                </Link>

                <span className="badge text-bg-success">
                  Active
                </span>
              </div>

              <div className="small text-secondary mt-1">
                {statusText}
                {' · '}
                {connectedCount}{' '}
                {connectedCount === 1
                  ? 'person connected'
                  : 'people connected'}
              </div>

              {speakingParticipants.length > 0 && (
                <div className="small text-success mt-1">
                  Speaking:{' '}
                  {speakingParticipants
                    .map(
                      (participation) =>
                        participation.user.id ===
                          currentUserId
                          ? 'you'
                          : `@${participation.user.username}`,
                    )
                    .join(', ')}
                </div>
              )}
            </div>
          </div>

          {(localError || error || roomError) && (
            <div
              className="alert alert-danger py-2 px-3 small mt-3 mb-0"
              role="alert"
            >
              {localError
                ?? error
                ?? roomError}
            </div>
          )}

          <div className="d-flex flex-wrap gap-2 mt-3">
            {ownsCurrentParticipation
              && mediaStatus ===
                'connected' && (
              <>
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  disabled={busy}
                  onClick={() => {
                    void runAction(
                      'microphone',
                      () =>
                        setMicrophoneEnabled(
                          !microphoneEnabled,
                        ),
                    )
                  }}
                >
                  {pendingAction ===
                  'microphone'
                    ? 'Updating…'
                    : microphoneEnabled
                      ? 'Mute'
                      : 'Unmute'}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  disabled={busy}
                  onClick={() => {
                    void runAction(
                      'audio',
                      startAudioPlayback,
                    )
                  }}
                >
                  {pendingAction ===
                  'audio'
                    ? 'Starting audio…'
                    : 'Enable audio'}
                </button>
              </>
            )}

            {ownsCurrentParticipation
              && mediaStatus ===
                'error' && (
              <button
                type="button"
                className="btn btn-outline-primary"
                disabled={busy}
                onClick={() => {
                  void runAction(
                    'retry',
                    refresh,
                  )
                }}
              >
                {pendingAction === 'retry'
                  ? 'Retrying…'
                  : 'Retry audio'}
              </button>
            )}

            <Link
              className="btn btn-outline-primary"
              to={`/voice/rooms/${roomId}`}
            >
              Open room
            </Link>

            {ownsCurrentParticipation && (
              <button
                type="button"
                className="btn btn-danger"
                disabled={busy}
                onClick={() => {
                  void runAction(
                    'leave',
                    () =>
                      leaveVoiceRoom(
                        roomId,
                      ),
                  )
                }}
              >
                {pendingAction === 'leave'
                  ? 'Leaving…'
                  : 'Leave voice'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


export default VoiceRoomOverlay
