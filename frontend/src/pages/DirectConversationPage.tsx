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
  sendDirectMessage,
} from '../api/messages'

import MessageComposer from '../components/messages/MessageComposer'
import MessageThread from '../components/messages/MessageThread'
import {
  mergeMessage,
  mergeMessageList,
} from '../components/messages/messageState'

import {
  useConversationRealtimeSubscription,
  useRealtimeEvent,
} from '../realtime/RealtimeContext'

import type {
  MessageCreatedPayload,
} from '../realtime/messageEvents'
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
  const { conversationId } =
    useParams<{
      conversationId: string
    }>()

  const parsedConversationId =
    Number(conversationId)

  const [
    conversation,
    setConversation,
  ] =
    useState<DirectConversation | null>(
      null,
    )

  const [messages, setMessages] =
    useState<Message[]>([])

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
              latest,
            ),
        )
      },
      [parsedConversationId],
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

        void refreshMessages()
      },
      [
        parsedConversationId,
        refreshMessages,
      ],
    )

  useRealtimeEvent<
    MessageCreatedPayload
  >(
    'message.created',
    handleMessageCreated,
  )

  useRealtimeEvent<
    ConversationSubscribedPayload
  >(
    'conversation.subscribed',
    handleSubscribed,
  )

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
          messagesResult,
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
    <section>
      <Link
        className="btn btn-link px-0 mb-3"
        to="/messages"
      >
        ← Back to messages
      </Link>

      <div className="card shadow-sm">
        <div className="card-header bg-white py-3">
          <h1 className="h4 mb-1">
            @{conversation
              .other_user
              .username}
          </h1>

          <div className="small text-secondary">
            Direct conversation #{conversation.id}
          </div>
        </div>

        <div
          className="card-body"
          style={{
            minHeight: '420px',
          }}
        >
          <MessageThread
            messages={messages}
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
          <MessageComposer
            placeholder={`Message @${conversation.other_user.username}`}
            replyingTo={replyingTo}
            onCancelReply={() =>
              setReplyingTo(null)
            }
            onSend={handleSend}
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
