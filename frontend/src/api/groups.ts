import {
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  apiRequest,
} from './client'
import { getAllPages } from './pagination'

import type {
  GroupConversation,
  GroupInvitation,
  GroupInvitationLink,
  GroupInvitationLinkSummary,
  GroupMembership,
} from '../types/groups'


export function getGroups():
Promise<GroupConversation[]> {
  return getAllPages<GroupConversation>(
    '/api/v1/groups/',
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


export function getGroupMembers(
  groupId: number,
): Promise<GroupMembership[]> {
  return getAllPages<GroupMembership>(
    `/api/v1/groups/${groupId}/members/`,
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


export function getIncomingGroupInvitations():
Promise<GroupInvitation[]> {
  return getAllPages<GroupInvitation>(
    '/api/v1/group-invitations/',
  )
}


export function getGroupPendingInvitations(
  groupId: number,
): Promise<GroupInvitation[]> {
  return getAllPages<GroupInvitation>(
    `/api/v1/groups/${groupId}/invitations/`,
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


export function cancelGroupInvitation(
  groupId: number,
  invitationId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/groups/${groupId}/invitations/${invitationId}/`,
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


export function getActiveGroupInvitationLinks(
  groupId: number,
): Promise<GroupInvitationLinkSummary[]> {
  return apiGet<GroupInvitationLinkSummary[]>(
    `/api/v1/groups/${groupId}/invitation-links/`,
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


export function updateGroupAvatar(
  groupId: number,
  avatar: File,
): Promise<GroupConversation> {
  const body = new FormData()
  body.append('avatar', avatar)
  return apiRequest<GroupConversation>(
    `/api/v1/groups/${groupId}/avatar/`,
    { method: 'PUT', body },
  )
}


export function removeGroupAvatar(
  groupId: number,
): Promise<GroupConversation> {
  return apiDelete<GroupConversation>(
    `/api/v1/groups/${groupId}/avatar/`,
  )
}
