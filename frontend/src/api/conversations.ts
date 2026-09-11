import {
  apiGet,
  apiPost,
} from './client'

import type { DirectConversation } from '../types/conversations'

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
  response: ListResponse<T>,
): T[] {
  if (Array.isArray(response)) {
    return response
  }

  return response.results
}

export async function getDirectConversations():
Promise<DirectConversation[]> {
  const response = await apiGet<
    ListResponse<DirectConversation>
  >('/api/v1/dms/')

  return unwrapList(response)
}

export function getDirectConversation(
  conversationId: number,
): Promise<DirectConversation> {
  return apiGet<DirectConversation>(
    `/api/v1/dms/${conversationId}/`,
  )
}

export function openDirectConversation(
  userId: number,
): Promise<DirectConversation> {
  return apiPost<DirectConversation>(
    '/api/v1/dms/',
    {
      user_id: userId,
    },
  )
}
