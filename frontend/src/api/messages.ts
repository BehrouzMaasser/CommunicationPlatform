import {
  apiPost,
} from './client'
import {
  getPaginatedPage,
  type PaginatedResponse,
} from './pagination'

import type {
  Message,
  MessageDraft,
} from '../types/messages'


function buildMessageBody(
  input: MessageDraft,
): Record<string, unknown> | FormData {
  const files = input.files ?? []

  if (files.length > 0) {
    const formData = new FormData()

    formData.append(
      'content',
      input.content,
    )

    if (input.replyToId !== undefined) {
      formData.append(
        'reply_to_id',
        String(input.replyToId),
      )
    }

    for (const file of files) {
      formData.append(
        'attachments',
        file,
      )
    }

    return formData
  }

  const body: Record<string, unknown> = {
    content: input.content,
  }

  if (input.replyToId !== undefined) {
    body.reply_to_id = input.replyToId
  }

  return body
}


export function getDirectMessages(
  conversationId: number,
): Promise<PaginatedResponse<Message>> {
  return getPaginatedPage<Message>(
    `/api/v1/dms/${conversationId}/messages/?page=last`,
  )
}


export function getGroupMessages(
  groupId: number,
): Promise<PaginatedResponse<Message>> {
  return getPaginatedPage<Message>(
    `/api/v1/groups/${groupId}/messages/?page=last`,
  )
}


export function getOlderMessages(
  pageUrl: string,
): Promise<PaginatedResponse<Message>> {
  return getPaginatedPage<Message>(
    pageUrl,
  )
}


export function sendDirectMessage(
  conversationId: number,
  input: MessageDraft,
): Promise<Message> {
  return apiPost<Message>(
    `/api/v1/dms/${conversationId}/messages/`,
    buildMessageBody(input),
  )
}


export function sendGroupMessage(
  groupId: number,
  input: MessageDraft,
): Promise<Message> {
  return apiPost<Message>(
    `/api/v1/groups/${groupId}/messages/`,
    buildMessageBody(input),
  )
}
