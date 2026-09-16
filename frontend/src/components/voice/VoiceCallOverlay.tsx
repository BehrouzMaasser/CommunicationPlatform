import {
  useState,
} from 'react'

import {
  useVoice,
} from '../../voice/useVoice'


type PendingAction =
  | 'accept'
  | 'reject'
  | 'cancel'
  | 'hangup'
  | 'microphone'
  | 'audio'
  | 'retry'
  | null


function describeError(
  error: unknown,
): string {
  if (error instanceof Error) {
    return error.message
  }

  return 'The voice action failed.'
}


function VoiceCallOverlay() {
  const {
    currentUserId,
    state,
    mediaStatus,
    ownsCurrentParticipation,
    microphoneEnabled,
    error,
    acceptDirectCall,
    rejectDirectCall,
    cancelDirectCall,
    endDirectCall,
    setMicrophoneEnabled,
    startAudioPlayback,
    getParticipantVolume,
    setParticipantVolume,
    toggleParticipantMuted,
    refresh,
  } = useVoice()

  const [
    pendingAction,
    setPendingAction,
  ] =
    useState<PendingAction>(null)

  const [
    localError,
    setLocalError,
  ] =
    useState<string | null>(null)

  const session = state.session

  if (
    !session
    || currentUserId === null
    || !session.caller
    || !session.recipient
    || session.group_id !== null
    || (
      session.status !== 'RINGING'
      &&
      session.status !== 'ACTIVE'
    )
  ) {
    return null
  }

  const isCaller =
    session.caller.id ===
      currentUserId

  const isRecipient =
    session.recipient.id ===
      currentUserId

  if (
    !isCaller
    && !isRecipient
  ) {
    return null
  }

  const otherUser =
    isCaller
      ? session.recipient
      : session.caller

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

  if (
    session.status === 'RINGING'
  ) {
    statusText =
      isCaller
        ? `Calling @${otherUser.username}…`
        : `@${otherUser.username} is calling you`
  } else if (
    !ownsCurrentParticipation
  ) {
    statusText =
      'Call active on another tab or device'
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

  return (
    <div
      className="position-fixed bottom-0 start-50 translate-middle-x p-3 w-100"
      style={{
        maxWidth: '34rem',
        zIndex: 1080,
      }}
      aria-live="polite"
    >
      <div className="card shadow-lg border-primary">
        <div className="card-body">
          <div className="d-flex align-items-start justify-content-between gap-3">
            <div className="min-w-0">
              <div className="fw-semibold text-truncate">
                Voice call with @{otherUser.username}
              </div>

              <div className="small text-secondary mt-1">
                {statusText}
              </div>
            </div>

            {session.status === 'RINGING' && (
              <span className="badge text-bg-warning">
                Ringing
              </span>
            )}

            {session.status === 'ACTIVE' && (
              <span className="badge text-bg-success">
                Active
              </span>
            )}
          </div>

          {(localError || error) && (
            <div
              className="alert alert-danger py-2 px-3 small mt-3 mb-0"
              role="alert"
            >
              {localError ?? error}
            </div>
          )}

          {session.status === 'ACTIVE'
            && ownsCurrentParticipation
            && mediaStatus ===
              'connected' && (
            <div className="mt-3">
              <div className="d-flex justify-content-between small mb-1">
                <span>
                  @{otherUser.username} volume
                </span>

                <span className="text-secondary">
                  {Math.round(
                    getParticipantVolume(
                      otherUser.id,
                    ) * 100,
                  )}%
                </span>
              </div>

              <div className="d-flex align-items-center gap-2">
                <input
                  className="form-range m-0"
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={
                    Math.round(
                      getParticipantVolume(
                        otherUser.id,
                      ) * 100,
                    )
                  }
                  aria-label={
                    `Volume for @${otherUser.username}`
                  }
                  onChange={(event) =>
                    setParticipantVolume(
                      otherUser.id,
                      Number(
                        event.target.value,
                      ) / 100,
                    )
                  }
                />

                <button
                  className="btn btn-sm btn-outline-secondary flex-shrink-0"
                  type="button"
                  onClick={() =>
                    toggleParticipantMuted(
                      otherUser.id,
                    )
                  }
                >
                  {getParticipantVolume(
                    otherUser.id,
                  ) === 0
                    ? 'Unmute'
                    : 'Mute'}
                </button>
              </div>
            </div>
          )}

          <div className="d-flex flex-wrap gap-2 mt-3">
            {session.status === 'RINGING'
              && isRecipient && (
              <>
                <button
                  type="button"
                  className="btn btn-success"
                  disabled={busy}
                  onClick={() => {
                    void runAction(
                      'accept',
                      () =>
                        acceptDirectCall(
                          session.id,
                        ),
                    )
                  }}
                >
                  {pendingAction === 'accept'
                    ? 'Accepting…'
                    : 'Accept'}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-danger"
                  disabled={busy}
                  onClick={() => {
                    void runAction(
                      'reject',
                      () =>
                        rejectDirectCall(
                          session.id,
                        ),
                    )
                  }}
                >
                  {pendingAction === 'reject'
                    ? 'Rejecting…'
                    : 'Reject'}
                </button>
              </>
            )}

            {session.status === 'RINGING'
              && isCaller && (
              <button
                type="button"
                className="btn btn-outline-danger"
                disabled={busy}
                onClick={() => {
                  void runAction(
                    'cancel',
                    () =>
                      cancelDirectCall(
                        session.id,
                      ),
                  )
                }}
              >
                {pendingAction === 'cancel'
                  ? 'Cancelling…'
                  : 'Cancel call'}
              </button>
            )}

            {session.status === 'ACTIVE' && (
              <>
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
                      {pendingAction === 'audio'
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

                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={busy}
                  onClick={() => {
                    void runAction(
                      'hangup',
                      () =>
                        endDirectCall(
                          session.id,
                        ),
                    )
                  }}
                >
                  {pendingAction === 'hangup'
                    ? 'Ending…'
                    : 'Hang up'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


export default VoiceCallOverlay
