import {
  useEffect,
  useState,
} from 'react'
import {
  Link,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import {
  getDirectConversation,
} from '../api/conversations'
import Avatar from '../components/users/Avatar'
import VoiceAudioSettings from '../components/voice/VoiceAudioSettings'
import {
  useVoice,
} from '../voice/useVoice'

import type {
  DirectConversation,
} from '../types/conversations'




type CallControlIconName =
  | 'microphone'
  | 'microphone-muted'
  | 'speaker'
  | 'speaker-muted'
  | 'end'


function CallControlIcon({
  name,
}: {
  name: CallControlIconName
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
    end:
      'M7.3 4.9a1 1 0 0 1 1.4 0L12 8.17l3.3-3.27a1 1 0 1 1 1.4 1.42L13.42 9.6l3.28 3.28a1 1 0 0 1-1.4 1.42L12 11.02 8.7 14.3a1 1 0 1 1-1.4-1.42l3.28-3.28L7.3 6.32a1 1 0 0 1 0-1.42Z',
  }

  return (
    <svg
      className="direct-call-control-svg"
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path d={paths[name]} />
    </svg>
  )
}

type PendingAction =
  | 'microphone'
  | 'audio-playback'
  | 'end'
  | 'retry'
  | 'take-over'
  | null


function describeError(
  error: unknown,
): string {
  if (error instanceof ApiError) {
    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}


function DirectCallPage() {
  const { conversationId } =
    useParams<{
      conversationId: string
    }>()

  const parsedConversationId =
    Number(conversationId)

  const validConversationId =
    Number.isInteger(
      parsedConversationId,
    )
    && parsedConversationId > 0

  const {
    currentUserId,
    state,
    mediaStatus,
    audioPlaybackRequired,
    ownsCurrentParticipation,
    microphoneEnabled,
    audioOutputMuted,
    speakingUserIds,
    mutedUserIds,
    error: voiceError,
    refresh,
    takeOverCurrentVoice,
    endDirectCall,
    setMicrophoneEnabled,
    setAudioOutputMuted,
    startAudioPlayback,
    getParticipantVolume,
    setParticipantVolume,
    toggleParticipantMuted,
  } = useVoice()

  const [conversation, setConversation] =
    useState<DirectConversation | null>(
      null,
    )

  const [loading, setLoading] =
    useState(true)

  const [pageError, setPageError] =
    useState<string | null>(null)

  const [actionError, setActionError] =
    useState<string | null>(null)

  const [pendingAction, setPendingAction] =
    useState<PendingAction>(null)


  useEffect(() => {
    if (!validConversationId) {
      return
    }

    let cancelled = false

    void getDirectConversation(
      parsedConversationId,
    )
      .then((result) => {
        if (!cancelled) {
          setConversation(result)
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setPageError(
            describeError(error),
          )
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [
    parsedConversationId,
    validConversationId,
  ])


  if (!validConversationId) {
    return (
      <section className="direct-call-page direct-call-page-state">
        <Link
          className="btn btn-link px-0"
          to="/messages"
        >
          ← Back to direct messages
        </Link>

        <div className="alert alert-danger mb-0">
          Invalid conversation id.
        </div>
      </section>
    )
  }


  if (loading) {
    return (
      <div className="direct-call-page-loading">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading call"
        />
      </div>
    )
  }


  if (
    pageError
    || !conversation
  ) {
    return (
      <section className="direct-call-page direct-call-page-state">
        <Link
          className="btn btn-link px-0"
          to="/messages"
        >
          ← Back to direct messages
        </Link>

        <div className="alert alert-danger mb-0">
          {pageError
            ?? 'Conversation not found.'}
        </div>
      </section>
    )
  }

  const otherUser =
    conversation.other_user

  const session = state.session

  const isActiveDirectCall =
    session?.status === 'ACTIVE'
    && session.group_id === null
    && session.caller !== null
    && session.recipient !== null
    && currentUserId !== null
    && (
      session.caller.id === otherUser.id
      || session.recipient.id === otherUser.id
    )

  const mediaControlsEnabled =
    isActiveDirectCall
    && ownsCurrentParticipation
    && mediaStatus === 'connected'

  const otherUserMuted =
    mutedUserIds.includes(
      otherUser.id,
    )

  const otherUserSpeaking =
    isActiveDirectCall
    && speakingUserIds.includes(
      otherUser.id,
    )
    && !otherUserMuted

  const participantVolume =
    getParticipantVolume(
      otherUser.id,
    )

  const participantVolumePercent =
    Math.round(
      participantVolume * 100,
    )

  const callStatusLabel =
    !isActiveDirectCall
      ? 'Call ended'
      : !ownsCurrentParticipation
        ? 'Active on another tab or device'
        : mediaStatus === 'connected'
          ? 'Connected'
          : mediaStatus === 'connecting'
            ? 'Connecting…'
            : mediaStatus === 'error'
              ? 'Connection problem'
              : 'Disconnected'


  async function handleMicrophoneToggle() {
    if (
      pendingAction !== null
      || !mediaControlsEnabled
    ) {
      return
    }

    setPendingAction('microphone')
    setActionError(null)

    try {
      await setMicrophoneEnabled(
        !microphoneEnabled,
      )
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setPendingAction(null)
    }
  }


  async function handleStartAudioPlayback() {
    if (
      pendingAction !== null
      || !isActiveDirectCall
      || !ownsCurrentParticipation
    ) {
      return
    }

    setPendingAction('audio-playback')
    setActionError(null)

    try {
      await startAudioPlayback()
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setPendingAction(null)
    }
  }


  async function handleRetry() {
    if (pendingAction !== null) {
      return
    }

    setPendingAction('retry')
    setActionError(null)

    try {
      await refresh()
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setPendingAction(null)
    }
  }


  async function handleTakeOver() {
    if (
      pendingAction !== null
      || !isActiveDirectCall
      || ownsCurrentParticipation
    ) {
      return
    }

    setPendingAction('take-over')
    setActionError(null)

    try {
      await takeOverCurrentVoice()
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setPendingAction(null)
    }
  }


  async function handleEndCall() {
    if (
      pendingAction !== null
      || !isActiveDirectCall
      || !session
    ) {
      return
    }

    setPendingAction('end')
    setActionError(null)

    try {
      await endDirectCall(
        session.id,
      )
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setPendingAction(null)
    }
  }


  return (
    <section className="direct-call-page">
      <div className="direct-call-page-card">
        <header className="direct-call-page-header">
          <Link
            className="direct-call-page-back"
            to={`/messages/dm/${conversation.id}`}
          >
            <span aria-hidden="true">←</span>
            <span>Back to chat</span>
          </Link>

          <VoiceAudioSettings buttonSize="md" />
        </header>

        <div className="direct-call-page-hero">
          <div
            className={`direct-call-page-avatar${otherUserSpeaking ? ' is-speaking' : ''}`}
          >
            <Avatar
              user={otherUser}
              size="xl"
              alt=""
            />
          </div>

          <div className="direct-call-page-identity">
            <h1 className="h3 mb-1">
              @{otherUser.username}
            </h1>

            <div
              className={`direct-call-page-status is-${mediaStatus}`}
            >
              {callStatusLabel}
            </div>

            <div
              className={`voice-remote-mute-indicator mt-2${otherUserMuted ? '' : ' invisible'}`}
              aria-hidden={!otherUserMuted}
            >
              Mic muted
            </div>
          </div>
        </div>

        {!isActiveDirectCall ? (
          <div className="direct-call-page-ended">
            <p className="mb-3 text-secondary">
              This direct call is no longer active.
            </p>
            <Link
              className="btn btn-primary"
              to={`/messages/dm/${conversation.id}`}
            >
              Return to chat
            </Link>
          </div>
        ) : (
          <>
            {!ownsCurrentParticipation && (
              <div className="alert alert-info direct-call-page-notice">
                <div className="mb-2">
                  This call is active on another tab or device. Reconnect here to move the call to this browser.
                </div>
                <button
                  className="btn btn-sm btn-primary"
                  type="button"
                  disabled={pendingAction !== null}
                  onClick={() => {
                    void handleTakeOver()
                  }}
                >
                  {pendingAction === 'take-over'
                    ? 'Reconnecting…'
                    : 'Reconnect here'}
                </button>
              </div>
            )}

            {audioPlaybackRequired && ownsCurrentParticipation && (
              <button
                className="btn btn-primary direct-call-page-enable-audio"
                type="button"
                disabled={pendingAction !== null}
                onClick={() => {
                  void handleStartAudioPlayback()
                }}
              >
                {pendingAction === 'audio-playback'
                  ? 'Enabling audio…'
                  : 'Enable call audio'}
              </button>
            )}

            <div className="direct-call-page-controls">
              <button
                className={`direct-call-control-button${microphoneEnabled ? '' : ' is-muted'}`}
                type="button"
                disabled={
                  pendingAction !== null
                  || !mediaControlsEnabled
                }
                aria-pressed={!microphoneEnabled}
                onClick={() => {
                  void handleMicrophoneToggle()
                }}
              >
                <span className="direct-call-control-icon">
                  <CallControlIcon
                    name={
                      microphoneEnabled
                        ? 'microphone'
                        : 'microphone-muted'
                    }
                  />
                </span>
                <span>
                  {microphoneEnabled
                    ? 'Mute mic'
                    : 'Unmute mic'}
                </span>
              </button>

              <button
                className={`direct-call-control-button${audioOutputMuted ? ' is-muted' : ''}`}
                type="button"
                disabled={!ownsCurrentParticipation}
                aria-pressed={audioOutputMuted}
                onClick={() => {
                  setAudioOutputMuted(
                    !audioOutputMuted,
                  )
                }}
              >
                <span className="direct-call-control-icon">
                  <CallControlIcon
                    name={
                      audioOutputMuted
                        ? 'speaker-muted'
                        : 'speaker'
                    }
                  />
                </span>
                <span>
                  {audioOutputMuted
                    ? 'Unmute audio'
                    : 'Mute audio'}
                </span>
              </button>

              <button
                className="direct-call-control-button is-danger"
                type="button"
                disabled={pendingAction !== null}
                onClick={() => {
                  void handleEndCall()
                }}
              >
                <span className="direct-call-control-icon">
                  <CallControlIcon name="end" />
                </span>
                <span>
                  {pendingAction === 'end'
                    ? 'Ending…'
                    : 'End call'}
                </span>
              </button>
            </div>

            <div className="direct-call-page-volume-card">
              <div className="direct-call-page-volume-heading">
                <div>
                  <div className="fw-semibold">
                    @{otherUser.username} volume
                  </div>
                  <div className="small text-secondary">
                    Adjust only this person's incoming audio.
                  </div>
                </div>

                <strong>
                  {participantVolumePercent}%
                </strong>
              </div>

              <input
                className="form-range direct-call-page-volume-slider"
                type="range"
                min="0"
                max="100"
                step="1"
                value={participantVolumePercent}
                disabled={!mediaControlsEnabled}
                aria-label={`Volume for @${otherUser.username}`}
                onChange={(event) => {
                  setParticipantVolume(
                    otherUser.id,
                    Number(
                      event.target.value,
                    ) / 100,
                  )
                }}
              />

              <button
                className="btn btn-outline-secondary direct-call-page-participant-mute"
                type="button"
                disabled={!mediaControlsEnabled}
                onClick={() => {
                  toggleParticipantMuted(
                    otherUser.id,
                  )
                }}
              >
                {participantVolume === 0
                  ? `Unmute @${otherUser.username}`
                  : `Mute @${otherUser.username}`}
              </button>
            </div>

            {voiceError
            && mediaStatus !== 'error'
            && ownsCurrentParticipation && (
              <div
                className="alert alert-warning direct-call-page-notice"
                role="alert"
              >
                {voiceError}
              </div>
            )}

            {mediaStatus === 'error' && ownsCurrentParticipation && (
              <div className="direct-call-page-retry">
                <div className="small text-danger">
                  {voiceError
                    ?? 'The voice connection has a problem.'}
                </div>
                <button
                  className="btn btn-sm btn-outline-primary"
                  type="button"
                  disabled={pendingAction !== null}
                  onClick={() => {
                    void handleRetry()
                  }}
                >
                  {pendingAction === 'retry'
                    ? 'Retrying…'
                    : 'Retry connection'}
                </button>
              </div>
            )}
          </>
        )}

        {actionError && (
          <div
            className="alert alert-danger direct-call-page-error mb-0"
            role="alert"
          >
            {actionError}
          </div>
        )}
      </div>
    </section>
  )
}


export default DirectCallPage
