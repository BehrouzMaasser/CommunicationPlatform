import {
  useState,
} from 'react'
import {
  useNavigate,
} from 'react-router-dom'

import type {
  PublicUser,
} from '../../types/users'

import {
  useVoice,
} from '../../voice/useVoice'

import VoiceAudioSettings from './VoiceAudioSettings'


type DirectCallButtonProps = {
  conversationId: number
  otherUser: PublicUser
  canCall: boolean
}


type PendingAction =
  | 'start'
  | null


function DirectCallButton({
  conversationId,
  otherUser,
  canCall,
}: DirectCallButtonProps) {
  const navigate = useNavigate()

  const {
    status,
    state,
    startDirectCall,
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


  if (sameActiveDirectCall) {
    return (
      <button
        className="btn btn-sm btn-outline-primary text-nowrap"
        type="button"
        title={`Open active call with @${otherUser.username}`}
        onClick={() => {
          navigate(
            `/messages/dm/${conversationId}/call`,
          )
        }}
      >
        Open call
      </button>
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

      <VoiceAudioSettings />

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
