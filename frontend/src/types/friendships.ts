import type { PublicUser } from './users'

export type FriendRequest = {
  id: number
  sender: PublicUser
  recipient: PublicUser
  created_at: string
}
