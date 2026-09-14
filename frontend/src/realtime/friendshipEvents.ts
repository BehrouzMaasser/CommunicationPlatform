import type {
  PublicUser,
} from '../types/users'


export type FriendRequestRealtimePayload = {
  request_id: number
  sender: PublicUser
  recipient: PublicUser
}


export type FriendRequestAcceptedRealtimePayload =
  FriendRequestRealtimePayload & {
    friendship_id: number
  }


export type FriendshipRemovedRealtimePayload = {
  user_a: PublicUser
  user_b: PublicUser
}
