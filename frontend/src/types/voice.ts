import type {
  PublicUser,
} from './users'


export type VoiceSession = {
  id: string
  kind: string
  status: string
  caller: PublicUser | null
  recipient: PublicUser | null
  group_id: number | null
  created_at: string
  ring_expires_at: string | null
  activated_at: string | null
  ended_at: string | null
  end_reason: string | null
}


export type VoiceParticipation = {
  id: string
  user: PublicUser
  role: string
  created_at: string
}


export type CurrentVoiceParticipation = {
  id: string
  role: string
  client_instance_id: string | null
  claimed_at: string | null
  created_at: string
}


export type VoiceState = {
  session: VoiceSession | null
  current_participation:
    CurrentVoiceParticipation | null
  participants: VoiceParticipation[]
}


export type VoiceMediaCredentials = {
  server_url: string
  participant_token: string
}
