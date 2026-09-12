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


export const friendshipRealtimeEventTypes = [
  'friend_request.created',
  'friend_request.accepted',
  'friend_request.rejected',
  'friend_request.cancelled',
  'friendship.removed',
] as const


export type FriendshipRealtimeEventType =
  typeof friendshipRealtimeEventTypes[number]
