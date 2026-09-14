import {
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Link,
  useNavigate,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { getGroup } from '../api/groups'
import {
  getGroupMessages,
  sendGroupMessage,
} from '../api/messages'

import MessageComposer from '../components/messages/MessageComposer'
import MessageThread from '../components/messages/MessageThread'
import {
  applyDeliveredReceipt,
  applyReadThroughReceipt,
  mergeMessage,
  mergeMessageList,
} from '../components/messages/messageState'

import {
  useConversationRealtimeSubscription,
  useRealtime,
  useRealtimeEvent,
} from '../realtime/RealtimeContext'

import type {
  MessageCreatedPayload,
  MessageDeliveredPayload,
  MessageReadPayload,
} from '../realtime/messageEvents'
import { useConversationTyping } from '../realtime/typing'
import type {
  GroupConversation,
} from '../types/groups'
import type {
  Message,
  MessageDraft,
} from '../types/messages'


function describeError(
  error: unknown,
): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return 'This group does not exist or you are not a current member.'
    }

    if (error.status === 401) {
      return 'Your session is not authenticated. Please sign in again.'
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}


type ConversationSubscribedPayload = {
  conversation_type:
    'dm' | 'group'
  conversation_id: number
}


function GroupConversationPage() {
  const {
    client: realtimeClient,
    status: realtimeStatus,
  } = useRealtime()
  const navigate = useNavigate()
  const { groupId } =
    useParams<{
      groupId: string
    }>()

  const parsedGroupId =
    Number(groupId)


  const {
    typingUsernames,
    notifyTyping,
    stopTyping,
  } = useConversationTyping(
    'group',
    parsedGroupId,
  )

  const [group, setGroup] =
    useState<GroupConversation | null>(
      null,
    )

  const [messages, setMessages] =
    useState<Message[]>([])

  const [isThreadAtBottom, setIsThreadAtBottom] =
    useState(false)

  const [
    replyingTo,
    setReplyingTo,
  ] =
    useState<Message | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const refreshMessages =
    useCallback(
      async () => {
        const latest =
          await getGroupMessages(
            parsedGroupId,
          )

        setMessages(
          (current) =>
            mergeMessageList(
              current,
              latest,
            ),
        )
      },
      [parsedGroupId],
    )

  const handleMessageCreated =
    useCallback(
      ({
        payload,
      }: {
        payload:
          MessageCreatedPayload
      }) => {
        if (
          payload
            .conversation_type
            !== 'group'
          ||
          payload
            .conversation_id
            !== parsedGroupId
        ) {
          return
        }

        setMessages(
          (current) =>
            mergeMessage(
              current,
              payload.message,
            ),
        )
      },
      [parsedGroupId],
    )

  const handleSubscribed =
    useCallback(
      ({
        payload,
      }: {
        payload:
          ConversationSubscribedPayload
      }) => {
        if (
          payload
            .conversation_type
            !== 'group'
          ||
          payload
            .conversation_id
            !== parsedGroupId
        ) {
          return
        }

        void refreshMessages()
      },
      [
        parsedGroupId,
        refreshMessages,
      ],
    )

  const handleGroupRenamed =
    useCallback(
      ({
        payload,
      }: {
        payload: {
          group_id: number
          name: string
        }
      }) => {
        if (
          payload.group_id !==
          parsedGroupId
        ) {
          return
        }

        setGroup(
          (current) =>
            current
              ? {
                  ...current,
                  name: payload.name,
                }
              : current,
        )
      },
      [parsedGroupId],
    )

  const handleGroupDeleted =
    useCallback(
      ({
        payload,
      }: {
        payload: {
          group_id: number
        }
      }) => {
        if (
          payload.group_id ===
          parsedGroupId
        ) {
          navigate('/groups')
        }
      },
      [
        navigate,
        parsedGroupId,
      ],
    )

  const handleUnsubscribed =
    useCallback(
      ({
        payload,
      }: {
        payload: {
          conversation_type:
            'dm' | 'group'
          conversation_id: number
          reason?: string
        }
      }) => {
        if (
          payload
            .conversation_type ===
              'group'
          &&
          payload
            .conversation_id ===
              parsedGroupId
          &&
          payload.reason ===
            'access_revoked'
        ) {
          navigate('/groups')
        }
      },
      [
        navigate,
        parsedGroupId,
      ],
    )

  const handleDelivered =
    useCallback(
      ({
        payload,
      }: {
        payload:
          MessageDeliveredPayload
      }) => {
        if (
          payload.conversation_type
            !== 'group'
          ||
          payload.conversation_id
            !== parsedGroupId
        ) {
          return
        }

        setMessages(
          (current) =>
            applyDeliveredReceipt(
              current,
              {
                messageId:
                  payload.message_id,
                userId:
                  payload.user_id,
                deliveredAt:
                  payload.delivered_at,
              },
            ),
        )
      },
      [parsedGroupId],
    )

  const handleRead =
    useCallback(
      ({
        payload,
      }: {
        payload:
          MessageReadPayload
      }) => {
        if (
          payload.conversation_type
            !== 'group'
          ||
          payload.conversation_id
            !== parsedGroupId
        ) {
          return
        }

        setMessages(
          (current) =>
            applyReadThroughReceipt(
              current,
              {
                throughMessageId:
                  payload.message_id,
                userId:
                  payload.user_id,
                readAt:
                  payload.read_at,
              },
            ),
        )
      },
      [parsedGroupId],
    )

  useRealtimeEvent<
    MessageCreatedPayload
  >(
    'message.created',
    handleMessageCreated,
  )


  useRealtimeEvent<
    MessageDeliveredPayload
  >(
    'message.delivered',
    handleDelivered,
  )

  useRealtimeEvent<
    MessageReadPayload
  >(
    'message.read',
    handleRead,
  )

  useRealtimeEvent<
    ConversationSubscribedPayload
  >(
    'conversation.subscribed',
    handleSubscribed,
  )

  useRealtimeEvent(
    'group.renamed',
    handleGroupRenamed,
  )

  useRealtimeEvent(
    'group.deleted',
    handleGroupDeleted,
  )

  useRealtimeEvent(
    'conversation.unsubscribed',
    handleUnsubscribed,
  )

  useEffect(() => {
    function markVisibleMessagesRead() {
      if (
        realtimeStatus !==
          'connected'
        ||
        document.visibilityState
          !== 'visible'
        ||
        !isThreadAtBottom
        ||
        messages.length === 0
      ) {
        return
      }

      const latest =
        messages[
          messages.length - 1
        ]

      realtimeClient.markReadThrough(
        latest.id,
      )
    }

    markVisibleMessagesRead()

    document.addEventListener(
      'visibilitychange',
      markVisibleMessagesRead,
    )

    return () => {
      document.removeEventListener(
        'visibilitychange',
        markVisibleMessagesRead,
      )
    }
  }, [
    isThreadAtBottom,
    messages,
    realtimeClient,
    realtimeStatus,
  ])

  useConversationRealtimeSubscription(
    'group',
    parsedGroupId,
    !loading &&
      group !== null,
  )

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (
        !Number.isInteger(
          parsedGroupId,
        ) ||
        parsedGroupId <= 0
      ) {
        setError(
          'Invalid group id.',
        )
        setLoading(false)
        return
      }

      try {
        const [
          groupResult,
          messagesResult,
        ] = await Promise.all([
          getGroup(
            parsedGroupId,
          ),
          getGroupMessages(
            parsedGroupId,
          ),
        ])

        if (cancelled) {
          return
        }

        setGroup(groupResult)
        setMessages(
          messagesResult,
        )
      } catch (requestError) {
        if (!cancelled) {
          setError(
            describeError(
              requestError,
            ),
          )
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [parsedGroupId])

  async function handleSend(
    input: MessageDraft,
  ) {
    const createdMessage =
      await sendGroupMessage(
        parsedGroupId,
        input,
      )

    setMessages(
      (current) =>
        mergeMessage(
          current,
          createdMessage,
        ),
    )

    setReplyingTo(null)
  }

  if (loading) {
    return (
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading group chat"
        />
      </div>
    )
  }

  if (
    error ||
    !group
  ) {
    return (
      <section>
        <Link
          className="btn btn-link px-0 mb-3"
          to="/groups"
        >
          ← Back to groups
        </Link>

        <div className="alert alert-danger">
          {error ??
            'Group not found.'}
        </div>
      </section>
    )
  }

  return (
    <section className="conversation-page">
      <div className="card shadow-sm conversation-card">
        <div className="card-header bg-white conversation-header">
          <div className="d-flex align-items-center justify-content-between gap-2">
            <h1 className="h5 mb-0 text-truncate">
              {group.name}
            </h1>

            <Link
              className="btn btn-outline-secondary btn-sm conversation-header-action"
              to={`/groups/${group.id}`}
            >
              Details
            </Link>
          </div>
        </div>

        <div className="card-body conversation-card-body">
          <MessageThread
            key={`group-${group.id}`}
            messages={messages}
            onAtBottomChange={
              setIsThreadAtBottom
            }
            onReply={(message) =>
              setReplyingTo(
                message,
              )
            }
          />
        </div>

        <div className="card-footer bg-white py-3">
          {typingUsernames.length > 0 && (
            <div className="small text-secondary mb-2">
              {typingUsernames.length === 1
                ? `@${typingUsernames[0]} is typing…`
                : `${typingUsernames.length} people are typing…`}
            </div>
          )}

          <MessageComposer
            placeholder={`Message ${group.name}`}
            replyingTo={replyingTo}
            onCancelReply={() =>
              setReplyingTo(null)
            }
            onSend={handleSend}
            onTyping={notifyTyping}
            onTypingStop={stopTyping}
          />
        </div>
      </div>
    </section>
  )
}


export default GroupConversationPage
