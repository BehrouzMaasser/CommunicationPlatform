import { createContext } from 'react'


export type ActivityState = {
  pendingFriendRequests: number
  pendingGroupInvitations: number
  pendingVoiceRoomInvitations: number
  unreadDirectMessages: number
  unreadGroupMessages: number
  directUnreadById: Record<number, number>
  groupUnreadById: Record<number, number>
}


export type ActivityContextValue = ActivityState & {
  getDirectUnread:
    (conversationId: number) => number
  getGroupUnread:
    (groupId: number) => number
  refreshActivity: () => Promise<void>
}


export const emptyActivityState: ActivityState = {
  pendingFriendRequests: 0,
  pendingGroupInvitations: 0,
  pendingVoiceRoomInvitations: 0,
  unreadDirectMessages: 0,
  unreadGroupMessages: 0,
  directUnreadById: {},
  groupUnreadById: {},
}


export const ActivityContext =
  createContext<
    ActivityContextValue | null
  >(null)
