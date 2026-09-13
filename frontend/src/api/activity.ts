import { apiGet } from './client'


export type ConversationUnreadSummary = {
  conversation_id: number
  unread_count: number
}


export type GroupUnreadSummary = {
  group_id: number
  unread_count: number
}


export type ActivitySummary = {
  pending_friend_requests: number
  pending_group_invitations: number
  unread_direct_messages: number
  unread_group_messages: number
  direct_conversations:
    ConversationUnreadSummary[]
  groups: GroupUnreadSummary[]
}


export function getActivitySummary():
Promise<ActivitySummary> {
  return apiGet<ActivitySummary>(
    '/api/v1/activity/summary/',
  )
}
