import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
} from './client'

import type {
  GroupConversation,
  GroupInvitation,
  GroupInvitationLink,
  GroupMembership,
} from '../types/groups'

type PaginatedResponse<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

type ListResponse<T> =
  | T[]
  | PaginatedResponse<T>

function unwrapList<T>(
  value: ListResponse<T>,
): T[] {
  return Array.isArray(value)
    ? value
    : value.results
}

export async function getGroups():
Promise<GroupConversation[]> {
  return unwrapList(
    await apiGet<ListResponse<GroupConversation>>(
      '/api/v1/groups/',
    ),
  )
}

export function createGroup(
  name: string,
): Promise<GroupConversation> {
  return apiPost<GroupConversation>(
    '/api/v1/groups/',
    { name },
  )
}

export function getGroup(
  groupId: number,
): Promise<GroupConversation> {
  return apiGet<GroupConversation>(
    `/api/v1/groups/${groupId}/`,
  )
}

export function renameGroup(
  groupId: number,
  name: string,
): Promise<GroupConversation> {
  return apiPatch<GroupConversation>(
    `/api/v1/groups/${groupId}/rename/`,
    { name },
  )
}

export function leaveGroup(
  groupId: number,
): Promise<unknown> {
  return apiPost(
    `/api/v1/groups/${groupId}/leave/`,
  )
}

export function disbandGroup(
  groupId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/groups/${groupId}/`,
  )
}

export async function getGroupMembers(
  groupId: number,
): Promise<GroupMembership[]> {
  return unwrapList(
    await apiGet<ListResponse<GroupMembership>>(
      `/api/v1/groups/${groupId}/members/`,
    ),
  )
}

export function removeGroupMember(
  groupId: number,
  userId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/groups/${groupId}/members/${userId}/`,
  )
}

export async function getIncomingGroupInvitations():
Promise<GroupInvitation[]> {
  return unwrapList(
    await apiGet<ListResponse<GroupInvitation>>(
      '/api/v1/group-invitations/',
    ),
  )
}

export async function getGroupPendingInvitations(
  groupId: number,
): Promise<GroupInvitation[]> {
  return unwrapList(
    await apiGet<ListResponse<GroupInvitation>>(
      `/api/v1/groups/${groupId}/invitations/`,
    ),
  )
}


export function inviteUserToGroup(
  groupId: number,
  userId: number,
): Promise<GroupInvitation> {
  return apiPost<GroupInvitation>(
    `/api/v1/groups/${groupId}/invitations/`,
    { user_id: userId },
  )
}

export function acceptGroupInvitation(
  invitationId: number,
): Promise<GroupMembership> {
  return apiPost<GroupMembership>(
    `/api/v1/group-invitations/${invitationId}/accept/`,
  )
}

export function rejectGroupInvitation(
  invitationId: number,
): Promise<unknown> {
  return apiPost(
    `/api/v1/group-invitations/${invitationId}/reject/`,
  )
}

export function createGroupInvitationLink(
  groupId: number,
): Promise<GroupInvitationLink> {
  return apiPost<GroupInvitationLink>(
    `/api/v1/groups/${groupId}/invitation-links/`,
  )
}

export function revokeGroupInvitationLink(
  groupId: number,
  linkId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/groups/${groupId}/invitation-links/${linkId}/`,
  )
}

export function joinGroupWithToken(
  token: string,
): Promise<GroupMembership> {
  return apiPost<GroupMembership>(
    `/api/v1/group-invitations/${encodeURIComponent(token)}/join/`,
  )
}
