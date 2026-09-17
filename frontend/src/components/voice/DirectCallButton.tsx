import {
  useState,
} from 'react'

import type {
  PublicUser,
} from '../../types/users'

import {
  useVoice,
} from '../../voice/useVoice'


type DirectCallButtonProps = {
  otherUser: PublicUser
  canCall: boolean
}


type PendingAction =
  | 'start'
  | 'end'
  | null


function DirectCallButton({
  otherUser,
  canCall,
}: DirectCallButtonProps) {
  const {
    status,
    state,
    mediaStatus,
    ownsCurrentParticipation,
    startDirectCall,
    endDirectCall,
    getParticipantVolume,
    setParticipantVolume,
    toggleParticipantMuted,
  } = useVoice()

  const [pendingAction, setPendingAction] =
    useState<PendingAction>(null)

  const [localError, setLocalError] =
    useState<string | null>(null)

  const session = state.session

  const hasOpenVoiceSession =
    session !== null
    && (
      session.status === 'RINGING'
      || session.status === 'ACTIVE'
    )

  const sameDirectCall =
    hasOpenVoiceSession
    && session.group_id === null
    && (
      session.caller?.id === otherUser.id
      || session.recipient?.id === otherUser.id
    )

  const sameActiveDirectCall =
    sameDirectCall
    && session?.status === 'ACTIVE'

  const busy =
    pendingAction !== null


  async function handleStartCall() {
    if (
      busy
      || !canCall
      || hasOpenVoiceSession
      || status !== 'ready'
    ) {
      return
    }

    setPendingAction('start')
    setLocalError(null)

    try {
      await startDirectCall(
        otherUser.id,
      )
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : 'Could not start the voice call.',
      )
    } finally {
      setPendingAction(null)
    }
  }


  async function handleEndCall() {
    if (
      busy
      || !sameActiveDirectCall
      || !session
    ) {
      return
    }

    setPendingAction('end')
    setLocalError(null)

    try {
      await endDirectCall(
        session.id,
      )
    } catch (error) {
      setLocalError(
        error instanceof Error
          ? error.message
          : 'Could not end the voice call.',
      )
    } finally {
      setPendingAction(null)
    }
  }


  if (
    sameActiveDirectCall
    && session
  ) {
    const volume =
      getParticipantVolume(
        otherUser.id,
      )

    const mediaControlsEnabled =
      ownsCurrentParticipation
      && mediaStatus === 'connected'

    return (
      <div className="direct-call-active-controls">
        <label
          className="direct-call-volume-control"
          title={`Volume for @${otherUser.username}`}
        >
          <span className="visually-hidden">
            Volume for @{otherUser.username}
          </span>
          <input
            className="form-range m-0"
            type="range"
            min="0"
            max="100"
            step="5"
            value={
              Math.round(
                volume * 100,
              )
            }
            disabled={
              !mediaControlsEnabled
            }
            aria-label={
              `Volume for @${otherUser.username}`
            }
            onChange={(event) => {
              setParticipantVolume(
                otherUser.id,
                Number(
                  event.target.value,
                ) / 100,
              )
            }}
          />
        </label>

        <button
          className="btn btn-sm btn-outline-secondary text-nowrap"
          type="button"
          disabled={
            !mediaControlsEnabled
          }
          onClick={() => {
            toggleParticipantMuted(
              otherUser.id,
            )
          }}
        >
          {volume === 0
            ? 'Unmute'
            : 'Mute'}
        </button>

        <button
          className="btn btn-sm btn-outline-danger text-nowrap"
          type="button"
          disabled={busy}
          onClick={() => {
            void handleEndCall()
          }}
        >
          {pendingAction === 'end'
            ? 'Ending…'
            : 'End call'}
        </button>

        {localError && (
          <span
            className="small text-danger"
            title={localError}
          >
            Call action failed
          </span>
        )}
      </div>
    )
  }


  let label = 'Call'
  let title =
    `Call @${otherUser.username}`

  let disabled = false

  if (pendingAction === 'start') {
    label = 'Calling…'
    disabled = true
  } else if (!canCall) {
    title =
      'You must be friends to start a voice call.'
    disabled = true
  } else if (
    status === 'loading'
  ) {
    label = 'Voice…'
    title =
      'Voice is loading.'
    disabled = true
  } else if (
    status === 'unavailable'
    || status === 'disabled'
  ) {
    label = 'Voice unavailable'
    title =
      'Voice communication is currently unavailable.'
    disabled = true
  } else if (
    status === 'error'
  ) {
    label = 'Voice error'
    title =
      'Voice state could not be loaded.'
    disabled = true
  } else if (sameDirectCall) {
    label = 'Ringing…'
    disabled = true
  } else if (hasOpenVoiceSession) {
    label = 'Voice busy'
    title =
      'Finish your current voice session first.'
    disabled = true
  }


  return (
    <div className="d-flex align-items-center gap-2">
      <button
        type="button"
        className="btn btn-sm btn-outline-primary text-nowrap"
        title={title}
        disabled={disabled}
        onClick={() => {
          void handleStartCall()
        }}
      >
        {label}
      </button>

      {localError && (
        <span
          className="small text-danger"
          title={localError}
        >
          Call failed
        </span>
      )}
    </div>
  )
}


export default DirectCallButton
