import type { PublicUser } from './users'

export type DirectConversation = {
  id: number
  other_user: PublicUser
  created_at: string
  last_activity_at: string
}
