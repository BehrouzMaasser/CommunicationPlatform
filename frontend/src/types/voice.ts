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
  voice_room_id: string | null
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



export type VoiceAudioOutputDevice = {
  device_id: string
  label: string
}



export type VoiceRoom = {
  id: string
  name: string
  avatar_url: string | null
  owner: PublicUser
  member_count: number
  connected_count: number
  created_at: string
  updated_at: string
}


export type VoiceRoomMembership = {
  id: string
  user: PublicUser
  joined_at: string
}



export type VoiceRoomInvitation = {
  id: string
  room_id: string
  room_name: string
  room_avatar_url: string | null
  invited_by: PublicUser
  recipient: PublicUser
  created_at: string
}


export type VoiceRoomInvitationLink = {
  id: string
  created_by: PublicUser
  token: string | null
  created_at: string
  expires_at: string
  revoked_at: string | null
}
