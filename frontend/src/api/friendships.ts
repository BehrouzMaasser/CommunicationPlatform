import {
  apiDelete,
  apiPost,
} from './client'
import { getAllPages } from './pagination'

import type {
  FriendRequest,
} from '../types/friendships'
import type { PublicUser } from '../types/users'


export function getFriends(): Promise<PublicUser[]> {
  return getAllPages<PublicUser>(
    '/api/v1/friends/',
  )
}


export function getIncomingFriendRequests():
Promise<FriendRequest[]> {
  return getAllPages<FriendRequest>(
    '/api/v1/friend-requests/incoming/',
  )
}


export function getOutgoingFriendRequests():
Promise<FriendRequest[]> {
  return getAllPages<FriendRequest>(
    '/api/v1/friend-requests/outgoing/',
  )
}


export function sendFriendRequest(
  userId: number,
): Promise<FriendRequest> {
  return apiPost<FriendRequest>(
    '/api/v1/friend-requests/',
    {
      user_id: userId,
    },
  )
}


export function acceptFriendRequest(
  requestId: number,
): Promise<unknown> {
  return apiPost(
    `/api/v1/friend-requests/${requestId}/accept/`,
  )
}


export function rejectFriendRequest(
  requestId: number,
): Promise<unknown> {
  return apiPost(
    `/api/v1/friend-requests/${requestId}/reject/`,
  )
}


export function cancelFriendRequest(
  requestId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/friend-requests/${requestId}/`,
  )
}


export function unfriend(
  friendUserId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/friends/${friendUserId}/`,
  )
}
