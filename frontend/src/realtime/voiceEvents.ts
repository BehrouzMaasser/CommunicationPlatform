export const VOICE_REALTIME_EVENT_TYPES = [
  'voice.direct_call.ringing',
  'voice.direct_call.accepted',
  'voice.direct_call.rejected',
  'voice.direct_call.cancelled',
  'voice.direct_call.missed',
  'voice.direct_call.ended',
  'voice.group.participant_joined',
  'voice.group.participant_left',
  'voice.group.participant_revoked',
  'voice.group.session_ended',
  'voice.room.participant_joined',
  'voice.room.participant_left',
  'voice.room.participant_revoked',
  'voice.room.session_ended',
] as const


export type VoiceRealtimeEventType =
  typeof VOICE_REALTIME_EVENT_TYPES[
    number
  ]


export type DirectCallRingingPayload = {
  session_id: string
  caller_id: number
  recipient_id: number
  ring_expires_at: string
}


export type DirectCallAcceptedPayload = {
  session_id: string
  caller_id: number
  recipient_id: number
  accepted_by_client_instance_id:
    string
  activated_at: string
}


export type DirectCallEndedPayload = {
  session_id: string
  caller_id: number
  recipient_id: number
  end_reason: string
  ended_at: string
}


export type GroupVoiceParticipantPayload = {
  session_id: string
  participation_id: string
  group_id: number
  user_id: number
}


export type GroupVoiceParticipantLeftPayload =
  GroupVoiceParticipantPayload & {
    session_ended: boolean
  }


export type GroupVoiceSessionEndedPayload = {
  session_id: string
  group_id: number
  end_reason: string
  ended_at: string
}
