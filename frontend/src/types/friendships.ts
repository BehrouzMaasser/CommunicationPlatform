import type { PublicUser } from './users'

export type FriendRequest = {
  id: number
  sender: PublicUser
  recipient: PublicUser
  created_at: string
}

export type PaginatedResponse<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
