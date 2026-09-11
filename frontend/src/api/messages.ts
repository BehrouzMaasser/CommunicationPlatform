import {
  apiGet,
  apiPost,
} from './client'

import type {
  Message,
  PaginatedMessages,
} from '../types/messages'


type SendDirectMessageInput = {
  content: string
  replyToId?: number
  files?: File[]
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
  input: SendDirectMessageInput,
): Promise<Message> {
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

    return apiPost<Message>(
      `/api/v1/dms/${conversationId}/messages/`,
      formData,
    )
  }

  const body: Record<string, unknown> = {
    content: input.content,
  }

  if (input.replyToId !== undefined) {
    body.reply_to_id = input.replyToId
  }

  return apiPost<Message>(
    `/api/v1/dms/${conversationId}/messages/`,
    body,
  )
}
