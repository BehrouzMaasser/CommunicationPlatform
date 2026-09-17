import type { PublicUser } from './users'

export type GroupConversation = {
  id: number
  name: string
  avatar_url: string | null
  created_at: string
  last_activity_at: string
}

export type GroupRole = 'OWNER' | 'MEMBER'

export type GroupMembership = {
  user: PublicUser
  role: GroupRole
  joined_at: string
}

export type GroupInvitation = {
  id: number
  group: GroupConversation
  invited_by: PublicUser
  recipient: PublicUser
  created_at: string
}

export type GroupInvitationLink = {
  id: number
  token: string
  created_at: string
  expires_at: string
}


export type GroupInvitationLinkSummary = {
  id: number
  token: string | null
  created_by: PublicUser
  created_at: string
  expires_at: string
}
