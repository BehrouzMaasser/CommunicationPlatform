import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'

import type {
  CSSProperties,
  PointerEvent as ReactPointerEvent,
} from 'react'

import {
  useNavigate,
} from 'react-router-dom'

import {
  getDirectConversations,
  openDirectConversation,
} from '../../api/conversations'
import {
  getVoiceRoom,
} from '../../api/voice'
import {
  useRealtimeEvent,
} from '../../realtime/useRealtime'
import {
  useVoice,
} from '../../voice/useVoice'

import type {
  VoiceRoom,
} from '../../types/voice'


type PendingAction =
  | 'audio'
  | 'microphone'
  | 'navigate'
  | null


type DragState = {
  pointerId: number
  startPointerX: number
  startPointerY: number
  startLeft: number
  startTop: number
  originX: number
  originY: number
  moved: boolean
}


type RoomRenamedPayload = {
  room_id: string
}


function clamp(
  value: number,
  minimum: number,
  maximum: number,
) {
  if (maximum < minimum) {
    return minimum
  }

  return Math.min(
    maximum,
    Math.max(minimum, value),
  )
}


function getInitials(
  value: string,
) {
  const words = value
    .replace(/^@/, '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)

  if (words.length === 0) {
    return 'V'
  }

  if (words.length === 1) {
    return words[0]
      .slice(0, 2)
      .toUpperCase()
  }

  return (
    words[0][0]
    + words[words.length - 1][0]
  ).toUpperCase()
}


function VoiceDockIcon({
  name,
}: {
  name:
    | 'microphone'
    | 'microphone-muted'
    | 'speaker'
    | 'speaker-muted'
}) {
  const paths = {
    microphone:
      'M12 3a4 4 0 0 0-4 4v5a4 4 0 1 0 8 0V7a4 4 0 0 0-4-4Zm-7 9a1 1 0 1 1 2 0 5 5 0 0 0 10 0 1 1 0 1 1 2 0 7 7 0 0 1-6 6.92V21h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-2.08A7 7 0 0 1 5 12Z',
    'microphone-muted':
      'm4.7 3.3 16 16-1.4 1.4-3.43-3.43A6.96 6.96 0 0 1 13 18.92V21h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-2.08A7 7 0 0 1 5 12a1 1 0 1 1 2 0 5 5 0 0 0 7.42 4.37l-1.5-1.5A4 4 0 0 1 8 12V9.83L3.3 4.7 4.7 3.3ZM12 3a4 4 0 0 1 4 4v5c0 .47-.08.92-.23 1.34l-1.8-1.8V7a1.97 1.97 0 0 0-3.35-1.42L9.2 4.16A3.98 3.98 0 0 1 12 3Zm7 9a1 1 0 0 1 2 0c0 1.45-.44 2.8-1.2 3.92l-1.47-1.47c.43-.72.67-1.55.67-2.45Z',
    speaker:
      'M4 9h4l5-4v14l-5-4H4V9Zm11.5.25a1 1 0 0 1 1.41.08 4 4 0 0 1 0 5.34 1 1 0 1 1-1.49-1.34 2 2 0 0 0 0-2.66 1 1 0 0 1 .08-1.42Zm2.92-2.68a1 1 0 0 1 1.41.08 8 8 0 0 1 0 10.7 1 1 0 1 1-1.49-1.34 6 6 0 0 0 0-8.02 1 1 0 0 1 .08-1.42Z',
    'speaker-muted':
      'M4 9h4l5-4v14l-5-4H4V9Zm12.3.3 1.7 1.7 1.7-1.7 1.4 1.4-1.7 1.7 1.7 1.7-1.4 1.4-1.7-1.7-1.7 1.7-1.4-1.4 1.7-1.7-1.7-1.7 1.4-1.4Z',
  }

  return (
    <svg
      className="voice-dock-icon"
      viewBox="0 0 24 24"
      focusable="false"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  )
}


function GlobalVoiceDock() {
  const navigate = useNavigate()

  const {
    currentUserId,
    state,
    mediaStatus,
    audioPlaybackRequired,
    ownsCurrentParticipation,
    microphoneEnabled,
    audioOutputMuted,
    speakingUserIds,
    setMicrophoneEnabled,
    setAudioOutputMuted,
    startAudioPlayback,
    refresh,
  } = useVoice()

  const [room, setRoom] =
    useState<VoiceRoom | null>(null)

  const [pendingAction, setPendingAction] =
    useState<PendingAction>(null)

  const [dragPosition, setDragPosition] =
    useState({
      sessionId: null as string | null,
      x: 0,
      y: 0,
    })

  const dockRef =
    useRef<HTMLDivElement | null>(null)

  const dragStateRef =
    useRef<DragState | null>(null)

  const suppressClickRef =
    useRef(false)

  const session = state.session

  const activeRoomId =
    session?.kind === 'ROOM'
    && session.status === 'ACTIVE'
      ? session.voice_room_id
      : null

  const directCallUser =
    session?.status === 'ACTIVE'
    && session.group_id === null
    && session.caller !== null
    && session.recipient !== null
    && currentUserId !== null
      ? (
          session.caller.id === currentUserId
            ? session.recipient
            : session.caller
        )
      : null

  const visible =
    activeRoomId !== null
    || directCallUser !== null

  const activeRoom =
    room?.id === activeRoomId
      ? room
      : null

  const offset =
    dragPosition.sessionId ===
      (session?.id ?? null)
      ? dragPosition
      : { x: 0, y: 0 }

  const label =
    activeRoomId !== null
      ? activeRoom?.name ?? 'Voice Room'
      : directCallUser !== null
        ? `@${directCallUser.username}`
        : 'Voice'

  const initials =
    getInitials(label)

  const speaking =
    visible
    && state.participants.some(
      (participation) =>
        speakingUserIds.includes(
          participation.user.id,
        )
        && (
          participation.user.id !== currentUserId
          || microphoneEnabled
        ),
    )

  const mediaControlsEnabled =
    ownsCurrentParticipation
    && (
      mediaStatus === 'connected'
      || mediaStatus === 'error'
    )

  const connectionStatus =
    ownsCurrentParticipation
      ? mediaStatus
      : 'disconnected'

  const connectionLabel = {
    connected: 'Voice connection established',
    connecting: 'Voice connection is connecting',
    disconnected: 'Voice connection is disconnected',
    error: 'Voice connection has an error',
  }[connectionStatus]

  const dockStyle = {
    '--voice-dock-x': `${offset.x}px`,
    '--voice-dock-y': `${offset.y}px`,
  } as CSSProperties


  const loadRoom =
    useCallback(
      async (roomId: string) => {
        try {
          setRoom(
            await getVoiceRoom(roomId),
          )
        } catch {
          setRoom(null)
        }
      },
      [],
    )


  useEffect(
    () => {
      if (!activeRoomId) {
        return
      }

      let cancelled = false

      void getVoiceRoom(activeRoomId)
        .then((nextRoom) => {
          if (!cancelled) {
            setRoom(nextRoom)
          }
        })
        .catch(() => {
          if (!cancelled) {
            setRoom(null)
          }
        })

      return () => {
        cancelled = true
      }
    },
    [activeRoomId],
  )


  useRealtimeEvent<RoomRenamedPayload>(
    'voice_room.renamed',
    useCallback(
      ({ payload }) => {
        if (
          activeRoomId
          && payload.room_id === activeRoomId
        ) {
          void loadRoom(activeRoomId)
        }
      },
      [
        activeRoomId,
        loadRoom,
      ],
    ),
  )


  useEffect(
    () => {
      function resetPosition() {
        setDragPosition({
          sessionId: session?.id ?? null,
          x: 0,
          y: 0,
        })
      }

      window.addEventListener(
        'resize',
        resetPosition,
      )

      return () => {
        window.removeEventListener(
          'resize',
          resetPosition,
        )
      }
    },
    [session?.id],
  )


  async function navigateToVoiceSource() {
    if (
      pendingAction === 'navigate'
      || !visible
    ) {
      return
    }

    if (activeRoomId) {
      navigate(
        `/voice/rooms/${activeRoomId}`,
      )
      return
    }

    if (!directCallUser) {
      return
    }

    setPendingAction('navigate')

    try {
      const conversations =
        await getDirectConversations()

      const existing =
        conversations.find(
          (conversation) =>
            conversation.other_user.id
              === directCallUser.id,
        )

      const conversation =
        existing
        ?? await openDirectConversation(
          directCallUser.id,
        )

      navigate(
        `/messages/dm/${conversation.id}`,
      )
    } catch {
      navigate('/messages')
    } finally {
      setPendingAction(null)
    }
  }


  async function handleAudioControl() {
    if (
      pendingAction !== null
      || !ownsCurrentParticipation
    ) {
      return
    }

    if (audioPlaybackRequired) {
      setPendingAction('audio')

      try {
        await startAudioPlayback()
      } catch {
        /* VoiceContext owns the user-facing media error. */
      } finally {
        setPendingAction(null)
      }

      return
    }

    if (mediaStatus === 'error') {
      setPendingAction('audio')

      try {
        await refresh()
      } finally {
        setPendingAction(null)
      }

      return
    }

    if (mediaStatus !== 'connected') {
      return
    }

    setAudioOutputMuted(
      !audioOutputMuted,
    )
  }


  async function handleMicrophoneControl() {
    if (
      pendingAction !== null
      || !ownsCurrentParticipation
      || mediaStatus !== 'connected'
    ) {
      return
    }

    setPendingAction('microphone')

    try {
      await setMicrophoneEnabled(
        !microphoneEnabled,
      )
    } catch {
      /* VoiceContext owns the user-facing media error. */
    } finally {
      setPendingAction(null)
    }
  }


  function isMobileDock() {
    return window.matchMedia(
      '(max-width: 400px)',
    ).matches
  }


  function handleDragStart(
    event: ReactPointerEvent<HTMLButtonElement>,
  ) {
    if (
      !isMobileDock()
      || event.button !== 0
      || !dockRef.current
    ) {
      return
    }

    const rect =
      dockRef.current.getBoundingClientRect()

    dragStateRef.current = {
      pointerId: event.pointerId,
      startPointerX: event.clientX,
      startPointerY: event.clientY,
      startLeft: rect.left,
      startTop: rect.top,
      originX: offset.x,
      originY: offset.y,
      moved: false,
    }

    event.currentTarget.setPointerCapture(
      event.pointerId,
    )
  }


  function handleDragMove(
    event: ReactPointerEvent<HTMLButtonElement>,
  ) {
    const drag = dragStateRef.current
    const dock = dockRef.current

    if (
      !drag
      || !dock
      || drag.pointerId !== event.pointerId
    ) {
      return
    }

    const deltaX =
      event.clientX - drag.startPointerX

    const deltaY =
      event.clientY - drag.startPointerY

    if (
      !drag.moved
      && Math.hypot(deltaX, deltaY) > 5
    ) {
      drag.moved = true
    }

    const topbar =
      document.querySelector<HTMLElement>(
        '.app-topbar',
      )

    const bottomNavigation =
      document.querySelector<HTMLElement>(
        '.app-mobile-bottom-nav',
      )

    const dockRect =
      dock.getBoundingClientRect()

    const topbarBottom =
      topbar?.getBoundingClientRect()
        .bottom ?? 0

    const bottomNavigationRect =
      bottomNavigation
        ?.getBoundingClientRect()

    const bottomLimit =
      bottomNavigationRect
      && bottomNavigationRect.height > 0
        ? bottomNavigationRect.top
        : window.innerHeight

    const margin = 8

    const desiredLeft = clamp(
      drag.startLeft + deltaX,
      margin,
      window.innerWidth
        - dockRect.width
        - margin,
    )

    const desiredTop = clamp(
      drag.startTop + deltaY,
      topbarBottom + margin,
      bottomLimit
        - dockRect.height
        - margin,
    )

    setDragPosition({
      sessionId: session?.id ?? null,
      x:
        drag.originX
        + desiredLeft
        - drag.startLeft,
      y:
        drag.originY
        + desiredTop
        - drag.startTop,
    })
  }


  function finishDrag(
    event: ReactPointerEvent<HTMLButtonElement>,
  ) {
    const drag = dragStateRef.current

    if (
      !drag
      || drag.pointerId !== event.pointerId
    ) {
      return
    }

    if (
      event.currentTarget.hasPointerCapture(
        event.pointerId,
      )
    ) {
      event.currentTarget.releasePointerCapture(
        event.pointerId,
      )
    }

    suppressClickRef.current =
      drag.moved

    if (drag.moved) {
      window.setTimeout(() => {
        suppressClickRef.current = false
      }, 0)
    }

    dragStateRef.current = null
  }


  if (!visible) {
    return null
  }


  const audioTitle =
    audioPlaybackRequired
      ? 'Enable incoming audio'
      : mediaStatus === 'error'
        ? 'Retry audio connection'
        : audioOutputMuted
          ? 'Unmute incoming audio'
          : 'Mute incoming audio'

  const microphoneTitle =
    microphoneEnabled
      ? 'Mute microphone'
      : 'Unmute microphone'


  return (
    <div
      ref={dockRef}
      className={`global-voice-dock connection-${connectionStatus}${speaking ? ' is-speaking' : ''}${mediaStatus === 'error' ? ' has-media-error' : ''}`}
      style={dockStyle}
      aria-label={`Active voice: ${label}. ${connectionLabel}.`}
    >
      <button
        className="voice-dock-destination"
        type="button"
        title="Open active voice. On mobile, drag to move."
        onPointerDown={handleDragStart}
        onPointerMove={handleDragMove}
        onPointerUp={finishDrag}
        onPointerCancel={finishDrag}
        onClick={() => {
          if (suppressClickRef.current) {
            suppressClickRef.current = false
            return
          }

          void navigateToVoiceSource()
        }}
      >
        <span
          className="voice-dock-connection-indicator"
          title={connectionLabel}
          aria-label={connectionLabel}
        />

        <span className="voice-dock-label-full">
          {label}
        </span>

        <span
          className="voice-dock-label-initials"
          aria-hidden="true"
        >
          {initials}
        </span>
      </button>

      <div className="voice-dock-controls">
        <button
          className={`voice-dock-control${audioOutputMuted ? ' is-muted' : ''}${audioPlaybackRequired ? ' needs-attention' : ''}`}
          type="button"
          title={audioTitle}
          aria-label={audioTitle}
          disabled={
            !ownsCurrentParticipation
            || (
              !mediaControlsEnabled
              && !audioPlaybackRequired
            )
          }
          onClick={() => {
            void handleAudioControl()
          }}
        >
          <VoiceDockIcon
            name={
              audioOutputMuted
                ? 'speaker-muted'
                : 'speaker'
            }
          />
        </button>

        <button
          className={`voice-dock-control${microphoneEnabled ? '' : ' is-muted'}`}
          type="button"
          title={microphoneTitle}
          aria-label={microphoneTitle}
          disabled={
            !ownsCurrentParticipation
            || mediaStatus !== 'connected'
          }
          onClick={() => {
            void handleMicrophoneControl()
          }}
        >
          <VoiceDockIcon
            name={
              microphoneEnabled
                ? 'microphone'
                : 'microphone-muted'
            }
          />
        </button>
      </div>
    </div>
  )
}


export default GlobalVoiceDock
