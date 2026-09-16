import {
  apiGet,
  apiPost,
} from './client'
import { getAllPages } from './pagination'

import type {
  VoiceMediaCredentials,
  VoiceRoom,
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
