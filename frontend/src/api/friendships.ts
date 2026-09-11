import {
  apiDelete,
  apiGet,
  apiPost,
} from './client'

import type {
  FriendRequest,
  PaginatedResponse,
} from '../types/friendships'
import type { PublicUser } from '../types/users'

type ListResponse<T> =
  | T[]
  | PaginatedResponse<T>

function unwrapList<T>(
  response: ListResponse<T>,
): T[] {
  if (Array.isArray(response)) {
    return response
  }

  return response.results
}

export async function getFriends(): Promise<PublicUser[]> {
  const response = await apiGet<
    ListResponse<PublicUser>
  >('/api/v1/friends/')

  return unwrapList(response)
}

export async function getIncomingFriendRequests():
Promise<FriendRequest[]> {
  const response = await apiGet<
    ListResponse<FriendRequest>
  >('/api/v1/friend-requests/incoming/')

  return unwrapList(response)
}

export async function getOutgoingFriendRequests():
Promise<FriendRequest[]> {
  const response = await apiGet<
    ListResponse<FriendRequest>
  >('/api/v1/friend-requests/outgoing/')

  return unwrapList(response)
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
