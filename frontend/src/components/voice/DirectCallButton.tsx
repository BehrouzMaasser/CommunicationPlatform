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


function DirectCallButton({
  otherUser,
  canCall,
}: DirectCallButtonProps) {
  const {
    status,
    state,
    startDirectCall,
  } = useVoice()

  const [starting, setStarting] =
    useState(false)

  const [
    localError,
    setLocalError,
  ] =
    useState<string | null>(null)

  const session = state.session

  const hasOpenVoiceSession =
    session !== null
    &&
    (
      session.status === 'RINGING'
      ||
      session.status === 'ACTIVE'
    )

  const sameDirectCall =
    hasOpenVoiceSession
    &&
    session.group_id === null
    &&
    (
      session.caller?.id ===
        otherUser.id
      ||
      session.recipient?.id ===
        otherUser.id
    )


  async function handleCall() {
    if (
      starting
      || !canCall
      || hasOpenVoiceSession
      || status !== 'ready'
    ) {
      return
    }

    setStarting(true)
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
      setStarting(false)
    }
  }


  let label = 'Call'
  let title =
    `Call @${otherUser.username}`

  let disabled = false

  if (starting) {
    label = 'Calling…'
    disabled = true
  } else if (!canCall) {
    label = 'Call'
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
    label =
      session?.status === 'RINGING'
        ? 'Ringing…'
        : 'In call'
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
          void handleCall()
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
