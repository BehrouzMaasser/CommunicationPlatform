import {
  apiDelete,
  apiGet,
  apiPost,
  apiRequest,
  apiPatch,
} from './client'
import { getAllPages } from './pagination'

import type {
  VoiceMediaCredentials,
  VoiceRoom,
  VoiceRoomInvitation,
  VoiceRoomInvitationLink,
  VoiceRoomMembership,
  VoiceState,
} from '../types/voice'


type ClientInstanceBody = {
  client_instance_id: string
}


type DirectCallStartBody =
  ClientInstanceBody & {
    user_id: number
  }


function sessionPath(
  sessionId: string,
): string {
  return encodeURIComponent(
    sessionId,
  )
}


export function getVoiceState():
Promise<VoiceState> {
  return apiGet<VoiceState>(
    '/api/v1/voice/state/',
  )
}


export function heartbeatCurrentVoice(
  clientInstanceId: string,
): Promise<void> {
  return apiPost<void>(
    '/api/v1/voice/state/heartbeat/',
    {
      client_instance_id:
        clientInstanceId,
    },
  )
}


export function takeOverCurrentVoice(
  clientInstanceId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    '/api/v1/voice/state/take-over/',
    {
      client_instance_id:
        clientInstanceId,
    },
  )
}


export function releaseCurrentVoice():
Promise<VoiceState> {
  return apiPost<VoiceState>(
    '/api/v1/voice/state/release/',
  )
}


export function startDirectCall(
  userId: number,
  clientInstanceId: string,
): Promise<VoiceState> {
  const body:
    DirectCallStartBody = {
      user_id: userId,
      client_instance_id:
        clientInstanceId,
    }

  return apiPost<VoiceState>(
    '/api/v1/voice/direct-calls/',
    body,
  )
}


export function acceptDirectCall(
  sessionId: string,
  clientInstanceId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    `/api/v1/voice/direct-calls/${sessionPath(sessionId)}/accept/`,
    {
      client_instance_id:
        clientInstanceId,
    },
  )
}


export function rejectDirectCall(
  sessionId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    `/api/v1/voice/direct-calls/${sessionPath(sessionId)}/reject/`,
  )
}


export function cancelDirectCall(
  sessionId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    `/api/v1/voice/direct-calls/${sessionPath(sessionId)}/cancel/`,
  )
}


export function endDirectCall(
  sessionId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    `/api/v1/voice/direct-calls/${sessionPath(sessionId)}/end/`,
  )
}


export function getVoiceMediaCredentials(
  sessionId: string,
  clientInstanceId: string,
): Promise<VoiceMediaCredentials> {
  return apiPost<VoiceMediaCredentials>(
    `/api/v1/voice/sessions/${sessionPath(sessionId)}/media-credentials/`,
    {
      client_instance_id:
        clientInstanceId,
    },
  )
}



export function getVoiceRooms():
Promise<VoiceRoom[]> {
  return getAllPages<VoiceRoom>(
    '/api/v1/voice/rooms/',
  )
}


export function createVoiceRoom(
  name: string,
): Promise<VoiceRoom> {
  return apiPost<VoiceRoom>(
    '/api/v1/voice/rooms/',
    { name },
  )
}



export function getVoiceRoom(
  roomId: string,
): Promise<VoiceRoom> {
  return apiGet<VoiceRoom>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/`,
  )
}


export function renameVoiceRoom(
  roomId: string,
  name: string,
): Promise<VoiceRoom> {
  return apiPatch<VoiceRoom>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/`,
    { name },
  )
}


export function deleteVoiceRoom(
  roomId: string,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/`,
  )
}


export function getVoiceRoomMembers(
  roomId: string,
): Promise<VoiceRoomMembership[]> {
  return getAllPages<VoiceRoomMembership>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/members/`,
  )
}


export function getVoiceRoomVoiceState(
  roomId: string,
): Promise<VoiceState> {
  return apiGet<VoiceState>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/voice/`,
  )
}


export function joinVoiceRoom(
  roomId: string,
  clientInstanceId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/voice/`,
    {
      client_instance_id:
        clientInstanceId,
    },
  )
}


export function leaveVoiceRoom(
  roomId: string,
  clientInstanceId: string,
): Promise<VoiceState> {
  return apiPost<VoiceState>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/voice/leave/`,
    {
      client_instance_id:
        clientInstanceId,
    },
  )
}



export function getIncomingVoiceRoomInvitations():
Promise<VoiceRoomInvitation[]> {
  return getAllPages<VoiceRoomInvitation>(
    '/api/v1/voice/room-invitations/',
  )
}


export function getVoiceRoomPendingInvitations(
  roomId: string,
): Promise<VoiceRoomInvitation[]> {
  return getAllPages<VoiceRoomInvitation>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/invitations/`,
  )
}


export function inviteUserToVoiceRoom(
  roomId: string,
  userId: number,
): Promise<VoiceRoomInvitation> {
  return apiPost<VoiceRoomInvitation>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/invitations/`,
    {
      user_id: userId,
    },
  )
}


export function cancelVoiceRoomInvitation(
  roomId: string,
  invitationId: string,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/invitations/${encodeURIComponent(invitationId)}/`,
  )
}


export function acceptVoiceRoomInvitation(
  invitationId: string,
): Promise<VoiceRoomMembership> {
  return apiPost<VoiceRoomMembership>(
    `/api/v1/voice/room-invitations/${encodeURIComponent(invitationId)}/accept/`,
  )
}


export function rejectVoiceRoomInvitation(
  invitationId: string,
): Promise<unknown> {
  return apiPost(
    `/api/v1/voice/room-invitations/${encodeURIComponent(invitationId)}/reject/`,
  )
}


export function getVoiceRoomInvitationLinks(
  roomId: string,
): Promise<VoiceRoomInvitationLink[]> {
  return getAllPages<VoiceRoomInvitationLink>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/invite-links/`,
  )
}


export function createVoiceRoomInvitationLink(
  roomId: string,
): Promise<VoiceRoomInvitationLink> {
  return apiPost<VoiceRoomInvitationLink>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/invite-links/`,
  )
}


export function revokeVoiceRoomInvitationLink(
  roomId: string,
  linkId: string,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/invite-links/${encodeURIComponent(linkId)}/`,
  )
}


export function joinVoiceRoomWithToken(
  token: string,
): Promise<VoiceRoomMembership> {
  return apiPost<VoiceRoomMembership>(
    '/api/v1/voice/room-invite-links/join/',
    {
      token,
    },
  )
}


export function leaveVoiceRoomMembership(
  roomId: string,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/members/me/`,
  )
}


export function removeVoiceRoomMember(
  roomId: string,
  userId: number,
): Promise<unknown> {
  return apiDelete(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/members/${userId}/`,
  )
}


export function updateVoiceRoomAvatar(
  roomId: string,
  avatar: File,
): Promise<VoiceRoom> {
  const body = new FormData()
  body.append('avatar', avatar)
  return apiRequest<VoiceRoom>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/avatar/`,
    { method: 'PUT', body },
  )
}


export function removeVoiceRoomAvatar(
  roomId: string,
): Promise<VoiceRoom> {
  return apiDelete<VoiceRoom>(
    `/api/v1/voice/rooms/${encodeURIComponent(roomId)}/avatar/`,
  )
}
