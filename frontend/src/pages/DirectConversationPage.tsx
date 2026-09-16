import {
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Link,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import {
  getDirectConversation,
} from '../api/conversations'
import { getFriends } from '../api/friendships'
import {
  getDirectMessages,
  getOlderMessages,
  sendDirectMessage,
} from '../api/messages'

import MessageComposer from '../components/messages/MessageComposer'
import MessageThread from '../components/messages/MessageThread'
import DirectCallButton from '../components/voice/DirectCallButton'
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
  FriendRequestAcceptedRealtimePayload,
  FriendshipRemovedRealtimePayload,
} from '../realtime/friendshipEvents'
import type {
  MessageCreatedPayload,
  MessageDeliveredPayload,
  MessageReadPayload,
} from '../realtime/messageEvents'
import { useConversationTyping } from '../realtime/typing'
import type {
  DirectConversation,
} from '../types/conversations'
import type {
  Message,
  MessageDraft,
} from '../types/messages'


function describeError(
  error: unknown,
): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return 'This direct conversation does not exist or you do not have access to it.'
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


function DirectConversationPage() {
  const {
    client: realtimeClient,
    status: realtimeStatus,
    currentUserId,
    isUserOnline,
  } = useRealtime()
  const { conversationId } =
    useParams<{
      conversationId: string
    }>()

  const parsedConversationId =
    Number(conversationId)


  const {
    typingUsernames,
    notifyTyping,
    stopTyping,
  } = useConversationTyping(
    'dm',
    parsedConversationId,
  )

  const [
    conversation,
    setConversation,
  ] =
    useState<DirectConversation | null>(
      null,
    )

  const [messages, setMessages] =
    useState<Message[]>([])

  const [olderMessagesUrl, setOlderMessagesUrl] =
    useState<string | null>(null)

  const [loadingOlderMessages, setLoadingOlderMessages] =
    useState(false)

  const [olderMessagesError, setOlderMessagesError] =
    useState<string | null>(null)

  const [isThreadAtBottom, setIsThreadAtBottom] =
    useState(false)

  const [
    replyingTo,
    setReplyingTo,
  ] =
    useState<Message | null>(null)

  const [
    canMessage,
    setCanMessage,
  ] = useState(false)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const refreshMessages =
    useCallback(
      async () => {
        const latest =
          await getDirectMessages(
            parsedConversationId,
          )

        setMessages(
          (current) =>
            mergeMessageList(
              current,
              latest.results,
            ),
        )
      },
      [parsedConversationId],
    )

  const refreshCanMessage =
    useCallback(
      async () => {
        if (!conversation) {
          return
        }

        const friends =
          await getFriends()

        setCanMessage(
          friends.some(
            (friend) =>
              friend.id ===
              conversation
                .other_user.id,
          ),
        )
      },
      [conversation],
    )


  const loadOlderMessages =
    useCallback(
      async () => {
        if (
          !olderMessagesUrl
          || loadingOlderMessages
        ) {
          return
        }

        setLoadingOlderMessages(true)
        setOlderMessagesError(null)

        try {
          const page =
            await getOlderMessages(
              olderMessagesUrl,
            )

          setMessages(
            (current) =>
              mergeMessageList(
                current,
                page.results,
              ),
          )
          setOlderMessagesUrl(
            page.previous,
          )
        } catch (requestError) {
          setOlderMessagesError(
            describeError(
              requestError,
            ),
          )
        } finally {
          setLoadingOlderMessages(false)
        }
      },
      [
        loadingOlderMessages,
        olderMessagesUrl,
      ],
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
            !== 'dm'
          ||
          payload
            .conversation_id
            !==
              parsedConversationId
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
      [parsedConversationId],
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
            !== 'dm'
          ||
          payload
            .conversation_id
            !==
              parsedConversationId
        ) {
          return
        }

        void Promise.all([
          refreshMessages(),
          refreshCanMessage(),
        ]).catch(() => {
          // The canonical page state remains usable;
          // the next reconnect or mutation can reconcile again.
        })
      },
      [
        parsedConversationId,
        refreshCanMessage,
        refreshMessages,
      ],
    )

  const handleFriendshipRemoved =
    useCallback(
      ({
        payload,
      }: {
        payload:
          FriendshipRemovedRealtimePayload
      }) => {
        if (
          currentUserId === undefined
          ||
          !conversation
        ) {
          return
        }

        const otherUserId =
          conversation.other_user.id

        const matchesConversation =
          (
            payload.user_a.id ===
              currentUserId
            &&
            payload.user_b.id ===
              otherUserId
          )
          ||
          (
            payload.user_b.id ===
              currentUserId
            &&
            payload.user_a.id ===
              otherUserId
          )

        if (!matchesConversation) {
          return
        }

        setCanMessage(false)
        setReplyingTo(null)
      },
      [
        conversation,
        currentUserId,
      ],
    )

  const handleFriendRequestAccepted =
    useCallback(
      ({
        payload,
      }: {
        payload:
          FriendRequestAcceptedRealtimePayload
      }) => {
        if (
          currentUserId === undefined
          ||
          !conversation
        ) {
          return
        }

        const otherUserId =
          conversation.other_user.id

        const matchesConversation =
          (
            payload.sender.id ===
              currentUserId
            &&
            payload.recipient.id ===
              otherUserId
          )
          ||
          (
            payload.recipient.id ===
              currentUserId
            &&
            payload.sender.id ===
              otherUserId
          )

        if (matchesConversation) {
          setCanMessage(true)
        }
      },
      [
        conversation,
        currentUserId,
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
            !== 'dm'
          ||
          payload.conversation_id
            !== parsedConversationId
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
      [parsedConversationId],
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
            !== 'dm'
          ||
          payload.conversation_id
            !== parsedConversationId
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
      [parsedConversationId],
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

  useRealtimeEvent<
    FriendshipRemovedRealtimePayload
  >(
    'friendship.removed',
    handleFriendshipRemoved,
  )

  useRealtimeEvent<
    FriendRequestAcceptedRealtimePayload
  >(
    'friend_request.accepted',
    handleFriendRequestAccepted,
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
    'dm',
    parsedConversationId,
    !loading &&
      conversation !== null,
  )

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (
        !Number.isInteger(
          parsedConversationId,
        ) ||
        parsedConversationId <= 0
      ) {
        setError(
          'Invalid conversation id.',
        )
        setLoading(false)
        return
      }

      try {
        const [
          conversationResult,
          messagesResult,
          friendsResult,
        ] = await Promise.all([
          getDirectConversation(
            parsedConversationId,
          ),
          getDirectMessages(
            parsedConversationId,
          ),
          getFriends(),
        ])

        if (cancelled) {
          return
        }

        setConversation(
          conversationResult,
        )

        setMessages(
          messagesResult.results,
        )
        setOlderMessagesUrl(
          messagesResult.previous,
        )

        setCanMessage(
          friendsResult.some(
            (friend) =>
              friend.id ===
              conversationResult
                .other_user.id,
          ),
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
  }, [parsedConversationId])

  async function handleSend(
    input: MessageDraft,
  ) {
    const createdMessage =
      await sendDirectMessage(
        parsedConversationId,
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
          aria-label="Loading conversation"
        />
      </div>
    )
  }

  if (
    error ||
    !conversation
  ) {
    return (
      <section>
        <Link
          className="btn btn-link px-0 mb-3"
          to="/messages"
        >
          ← Back to messages
        </Link>

        <div className="alert alert-danger">
          {error ??
            'Conversation not found.'}
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
              @{conversation
                .other_user
                .username}
            </h1>

            <div className="d-flex align-items-center gap-2">
              <span
                className={
                  isUserOnline(
                    conversation.other_user.id,
                  )
                    ? 'badge text-bg-success'
                    : 'badge text-bg-secondary'
                }
              >
                {
                  isUserOnline(
                    conversation.other_user.id,
                  )
                    ? 'Online'
                    : 'Offline'
                }
              </span>

              <DirectCallButton
                otherUser={
                  conversation.other_user
                }
                canCall={canMessage}
              />
            </div>
          </div>
        </div>

        <div className="card-body conversation-card-body">
          <MessageThread
            key={`dm-${conversation.id}`}
            messages={messages}
            hasOlderMessages={
              olderMessagesUrl !== null
            }
            loadingOlderMessages={
              loadingOlderMessages
            }
            olderMessagesError={
              olderMessagesError
            }
            onLoadOlderMessages={
              loadOlderMessages
            }
            onAtBottomChange={
              setIsThreadAtBottom
            }
            onReply={
              canMessage
                ? (message) =>
                    setReplyingTo(
                      message,
                    )
                : undefined
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
            placeholder={`Message @${conversation.other_user.username}`}
            replyingTo={replyingTo}
            onCancelReply={() =>
              setReplyingTo(null)
            }
            onSend={handleSend}
            onTyping={notifyTyping}
            onTypingStop={stopTyping}
            disabled={!canMessage}
            disabledMessage={
              !canMessage
                ? `You are no longer friends with @${conversation.other_user.username}. This conversation remains available as history, but new direct messages are disabled.`
                : undefined
            }
          />
        </div>
      </div>
    </section>
  )
}


export default DirectConversationPage
