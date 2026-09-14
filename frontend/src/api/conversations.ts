import {
  apiGet,
  apiPost,
} from './client'
import { getAllPages } from './pagination'

import type { DirectConversation } from '../types/conversations'


export function getDirectConversations():
Promise<DirectConversation[]> {
  return getAllPages<DirectConversation>(
    '/api/v1/dms/',
  )
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
