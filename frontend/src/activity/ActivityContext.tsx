import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  ActivityContext,
  emptyActivityState,
  type ActivityState,
} from './activityContextState'

import {
  getActivitySummary,
  type ActivitySummary,
} from '../api/activity'
import {
  useRealtime,
  useRealtimeEvent,
} from '../realtime/RealtimeContext'
import type {
  FriendRequestAcceptedRealtimePayload,
  FriendRequestRealtimePayload,
} from '../realtime/friendshipEvents'
import type {
  GroupInvitationAcceptedEventPayload,
  GroupInvitationEventPayload,
  GroupMemberEventPayload,
} from '../realtime/groupEvents'
import type {
  MessageCreatedPayload,
  MessageReadPayload,
} from '../realtime/messageEvents'


type ActivityNotice = {
  id: string
  message: string
}


type ActivityProviderProps = {
  enabled: boolean
  currentUserId?: number
  children: ReactNode
}


function fromSummary(
  summary: ActivitySummary,
): ActivityState {
  return {
    pendingFriendRequests:
      summary.pending_friend_requests,
    pendingGroupInvitations:
      summary.pending_group_invitations,
    pendingVoiceRoomInvitations:
      summary.pending_voice_room_invitations,
    unreadDirectMessages:
      summary.unread_direct_messages,
    unreadGroupMessages:
      summary.unread_group_messages,
    directUnreadById:
      Object.fromEntries(
        summary.direct_conversations.map(
          (item) => [
            item.conversation_id,
            item.unread_count,
          ],
        ),
      ),
    groupUnreadById:
      Object.fromEntries(
        summary.groups.map(
          (item) => [
            item.group_id,
            item.unread_count,
          ],
        ),
      ),
  }
}


function decrement(
  value: number,
): number {
  return Math.max(0, value - 1)
}


export function ActivityProvider({
  enabled,
  currentUserId,
  children,
}: ActivityProviderProps) {
  const { status } = useRealtime()

  const [state, setState] =
    useState<ActivityState>(
      emptyActivityState,
    )

  const [notices, setNotices] =
    useState<ActivityNotice[]>([])

  const reconcileTimer =
    useRef<number | null>(null)

  const noticeTimers =
    useRef<Map<string, number>>(
      new Map(),
    )

  const refreshActivity =
    useCallback(async () => {
      if (
        !enabled ||
        currentUserId === undefined
      ) {
        return
      }

      try {
        const summary =
          await getActivitySummary()

        setState(
          fromSummary(summary),
        )
      } catch {
        // Activity chrome must never make the rest of the application
        // unusable. Realtime changes continue optimistically and the next
        // reconnect/mutation will reconcile again.
      }
    }, [
      currentUserId,
      enabled,
    ])

  const scheduleReconcile =
    useCallback(() => {
      if (
        !enabled ||
        currentUserId === undefined
      ) {
        return
      }

      if (
        reconcileTimer.current
        !== null
      ) {
        window.clearTimeout(
          reconcileTimer.current,
        )
      }

      reconcileTimer.current =
        window.setTimeout(
          () => {
            reconcileTimer.current =
              null
            void refreshActivity()
          },
          350,
        )
    }, [
      currentUserId,
      enabled,
      refreshActivity,
    ])

  const dismissNotice =
    useCallback(
      (noticeId: string) => {
        setNotices(
          (current) =>
            current.filter(
              (notice) =>
                notice.id !==
                noticeId,
            ),
        )

        const timer =
          noticeTimers.current.get(
            noticeId,
          )

        if (timer !== undefined) {
          window.clearTimeout(timer)
          noticeTimers.current.delete(
            noticeId,
          )
        }
      },
      [],
    )

  const pushNotice =
    useCallback(
      (message: string) => {
        const id =
          crypto.randomUUID()

        setNotices(
          (current) => [
            ...current,
            { id, message },
          ].slice(-3),
        )

        const timer =
          window.setTimeout(
            () => {
              dismissNotice(id)
            },
            6000,
          )

        noticeTimers.current.set(
          id,
          timer,
        )
      },
      [dismissNotice],
    )

  useEffect(() => {
    if (!enabled) {
      if (
        reconcileTimer.current
        !== null
      ) {
        window.clearTimeout(
          reconcileTimer.current,
        )
        reconcileTimer.current = null
      }

      return
    }

    const initialRefreshTimer =
      window.setTimeout(
        () => {
          void refreshActivity()
        },
        0,
      )

    return () => {
      window.clearTimeout(
        initialRefreshTimer,
      )
    }
  }, [
    enabled,
    refreshActivity,
  ])

  useEffect(() => {
    if (
      enabled &&
      status === 'connected'
    ) {
      scheduleReconcile()
    }
  }, [
    enabled,
    scheduleReconcile,
    status,
  ])

  useEffect(
    () => () => {
      if (
        reconcileTimer.current
        !== null
      ) {
        window.clearTimeout(
          reconcileTimer.current,
        )
      }

      for (
        const timer
        of noticeTimers.current.values()
      ) {
        window.clearTimeout(timer)
      }

      noticeTimers.current.clear()
    },
    [],
  )

  const handleMessageCreated =
    useCallback(
      ({ payload }: {
        payload: MessageCreatedPayload
      }) => {
        if (
          currentUserId === undefined ||
          payload.message.sender.id ===
            currentUserId
        ) {
          return
        }

        setState((current) => {
          if (
            payload.conversation_type
            === 'dm'
          ) {
            const previous =
              current.directUnreadById[
                payload.conversation_id
              ] ?? 0

            return {
              ...current,
              unreadDirectMessages:
                current
                  .unreadDirectMessages
                + 1,
              directUnreadById: {
                ...current
                  .directUnreadById,
                [payload
                  .conversation_id]:
                  previous + 1,
              },
            }
          }

          const previous =
            current.groupUnreadById[
              payload.conversation_id
            ] ?? 0

          return {
            ...current,
            unreadGroupMessages:
              current
                .unreadGroupMessages
              + 1,
            groupUnreadById: {
              ...current
                .groupUnreadById,
              [payload
                .conversation_id]:
                previous + 1,
            },
          }
        })

        scheduleReconcile()
      },
      [
        currentUserId,
        scheduleReconcile,
      ],
    )

  const handleMessageRead =
    useCallback(
      ({ payload }: {
        payload: MessageReadPayload
      }) => {
        if (
          currentUserId === undefined ||
          payload.user_id !==
            currentUserId
        ) {
          return
        }

        setState((current) => {
          if (
            payload.conversation_type
            === 'dm'
          ) {
            const previous =
              current.directUnreadById[
                payload.conversation_id
              ] ?? 0
            const readCount =
              Math.min(
                previous,
                payload.read_count,
              )
            const nextCount =
              previous - readCount
            const directUnreadById = {
              ...current
                .directUnreadById,
            }

            if (nextCount > 0) {
              directUnreadById[
                payload.conversation_id
              ] = nextCount
            } else {
              delete directUnreadById[
                payload.conversation_id
              ]
            }

            return {
              ...current,
              unreadDirectMessages:
                Math.max(
                  0,
                  current
                    .unreadDirectMessages
                  - readCount,
                ),
              directUnreadById,
            }
          }

          const previous =
            current.groupUnreadById[
              payload.conversation_id
            ] ?? 0
          const readCount = Math.min(
            previous,
            payload.read_count,
          )
          const nextCount =
            previous - readCount
          const groupUnreadById = {
            ...current.groupUnreadById,
          }

          if (nextCount > 0) {
            groupUnreadById[
              payload.conversation_id
            ] = nextCount
          } else {
            delete groupUnreadById[
              payload.conversation_id
            ]
          }

          return {
            ...current,
            unreadGroupMessages:
              Math.max(
                0,
                current
                  .unreadGroupMessages
                - readCount,
              ),
            groupUnreadById,
          }
        })

        scheduleReconcile()
      },
      [
        currentUserId,
        scheduleReconcile,
      ],
    )

  const handleFriendRequestCreated =
    useCallback(
      ({ payload }: {
        payload:
          FriendRequestRealtimePayload
      }) => {
        if (
          payload.recipient.id !==
          currentUserId
        ) {
          return
        }

        setState((current) => ({
          ...current,
          pendingFriendRequests:
            current
              .pendingFriendRequests
            + 1,
        }))
        scheduleReconcile()
      },
      [
        currentUserId,
        scheduleReconcile,
      ],
    )

  const handleFriendRequestRemoved =
    useCallback(
      ({ payload }: {
        payload:
          FriendRequestRealtimePayload
      }) => {
        if (
          payload.recipient.id !==
          currentUserId
        ) {
          return
        }

        setState((current) => ({
          ...current,
          pendingFriendRequests:
            decrement(
              current
                .pendingFriendRequests,
            ),
        }))
        scheduleReconcile()
      },
      [
        currentUserId,
        scheduleReconcile,
      ],
    )

  const handleFriendRequestAccepted =
    useCallback(
      ({ payload }: {
        payload:
          FriendRequestAcceptedRealtimePayload
      }) => {
        handleFriendRequestRemoved({
          payload,
        })

        if (
          payload.sender.id ===
          currentUserId
        ) {
          pushNotice(
            `@${payload.recipient.username} accepted your friend request.`,
          )
        }
      },
      [
        currentUserId,
        handleFriendRequestRemoved,
        pushNotice,
      ],
    )

  const handleGroupInvitationCreated =
    useCallback(
      ({ payload }: {
        payload:
          GroupInvitationEventPayload
      }) => {
        if (
          payload.recipient_id !==
          currentUserId
        ) {
          return
        }

        setState((current) => ({
          ...current,
          pendingGroupInvitations:
            current
              .pendingGroupInvitations
            + 1,
        }))
        scheduleReconcile()
      },
      [
        currentUserId,
        scheduleReconcile,
      ],
    )

  const handleGroupInvitationRemoved =
    useCallback(
      ({ payload }: {
        payload:
          GroupInvitationEventPayload
      }) => {
        if (
          payload.recipient_id !==
          currentUserId
        ) {
          return
        }

        setState((current) => ({
          ...current,
          pendingGroupInvitations:
            decrement(
              current
                .pendingGroupInvitations,
            ),
        }))
        scheduleReconcile()
      },
      [
        currentUserId,
        scheduleReconcile,
      ],
    )

  const handleGroupInvitationAccepted =
    useCallback(
      ({ payload }: {
        payload:
          GroupInvitationAcceptedEventPayload
      }) => {
        handleGroupInvitationRemoved({
          payload,
        })

        if (
          payload.invited_by_id ===
          currentUserId
        ) {
          pushNotice(
            `@${payload.recipient_username} accepted your invitation to ${payload.group_name}.`,
          )
        }
      },
      [
        currentUserId,
        handleGroupInvitationRemoved,
        pushNotice,
      ],
    )

  const clearGroupUnread =
    useCallback(
      (groupId: number) => {
        setState((current) => {
          const unread =
            current.groupUnreadById[
              groupId
            ] ?? 0

          if (unread === 0) {
            return current
          }

          const groupUnreadById = {
            ...current.groupUnreadById,
          }
          delete groupUnreadById[
            groupId
          ]

          return {
            ...current,
            unreadGroupMessages:
              Math.max(
                0,
                current
                  .unreadGroupMessages
                - unread,
              ),
            groupUnreadById,
          }
        })

        scheduleReconcile()
      },
      [scheduleReconcile],
    )

  const handleMemberRemoved =
    useCallback(
      ({ payload }: {
        payload: GroupMemberEventPayload
      }) => {
        if (
          payload.user_id ===
          currentUserId
        ) {
          clearGroupUnread(
            payload.group_id,
          )
        }
      },
      [
        clearGroupUnread,
        currentUserId,
      ],
    )

  const handleGroupDeleted =
    useCallback(
      ({ payload }: {
        payload: {
          group_id: number
        }
      }) => {
        clearGroupUnread(
          payload.group_id,
        )
      },
      [clearGroupUnread],
    )

  const handleVoiceRoomActivityChange =
    useCallback(
      () => {
        scheduleReconcile()
      },
      [scheduleReconcile],
    )


  useRealtimeEvent(
    'message.created',
    handleMessageCreated,
  )
  useRealtimeEvent(
    'message.read',
    handleMessageRead,
  )
  useRealtimeEvent(
    'friend_request.created',
    handleFriendRequestCreated,
  )
  useRealtimeEvent(
    'friend_request.accepted',
    handleFriendRequestAccepted,
  )
  useRealtimeEvent(
    'friend_request.rejected',
    handleFriendRequestRemoved,
  )
  useRealtimeEvent(
    'friend_request.cancelled',
    handleFriendRequestRemoved,
  )
  useRealtimeEvent(
    'group_invitation.created',
    handleGroupInvitationCreated,
  )
  useRealtimeEvent(
    'group_invitation.accepted',
    handleGroupInvitationAccepted,
  )
  useRealtimeEvent(
    'group_invitation.rejected',
    handleGroupInvitationRemoved,
  )
  useRealtimeEvent(
    'group_invitation.cancelled',
    handleGroupInvitationRemoved,
  )
  useRealtimeEvent(
    'group.member_removed',
    handleMemberRemoved,
  )
  useRealtimeEvent(
    'group.member_left',
    handleMemberRemoved,
  )
  useRealtimeEvent(
    'group.deleted',
    handleGroupDeleted,
  )


  useRealtimeEvent(
    'voice_room_invitation.created',
    handleVoiceRoomActivityChange,
  )
  useRealtimeEvent(
    'voice_room_invitation.accepted',
    handleVoiceRoomActivityChange,
  )
  useRealtimeEvent(
    'voice_room_invitation.rejected',
    handleVoiceRoomActivityChange,
  )
  useRealtimeEvent(
    'voice_room_invitation.cancelled',
    handleVoiceRoomActivityChange,
  )
  useRealtimeEvent(
    'voice_room.member_added',
    handleVoiceRoomActivityChange,
  )

  const visibleState =
    enabled
      ? state
      : emptyActivityState

  const value = useMemo(
    () => ({
      ...visibleState,
      getDirectUnread:
        (conversationId: number) =>
          visibleState.directUnreadById[
            conversationId
          ] ?? 0,
      getGroupUnread:
        (groupId: number) =>
          visibleState.groupUnreadById[
            groupId
          ] ?? 0,
      refreshActivity,
    }),
    [
      refreshActivity,
      visibleState,
    ],
  )

  return (
    <ActivityContext.Provider
      value={value}
    >
      {children}

      {enabled &&
        notices.length > 0 && (
        <div
          className="activity-toast-stack"
          aria-live="polite"
          aria-atomic="false"
        >
          {notices.map(
            (notice) => (
              <div
                className="activity-toast"
                key={notice.id}
                role="status"
              >
                <div>
                  {notice.message}
                </div>

                <button
                  className="btn-close"
                  type="button"
                  aria-label="Dismiss notification"
                  onClick={() =>
                    dismissNotice(
                      notice.id,
                    )
                  }
                />
              </div>
            ),
          )}
        </div>
      )}
    </ActivityContext.Provider>
  )
}
