import {
  apiGet,
  apiPost,
} from './client'

import type {
  Message,
  MessageDraft,
  PaginatedMessages,
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


export async function getDirectMessages(
  conversationId: number,
): Promise<Message[]> {
  const response =
    await apiGet<PaginatedMessages>(
      `/api/v1/dms/${conversationId}/messages/`,
    )

  return response.results
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


export async function getGroupMessages(
  groupId: number,
): Promise<Message[]> {
  const response =
    await apiGet<PaginatedMessages>(
      `/api/v1/groups/${groupId}/messages/`,
    )

  return response.results
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
