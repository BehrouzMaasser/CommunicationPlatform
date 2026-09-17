import {
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Outlet,
  useMatch,
  useNavigate,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { useActivity } from '../activity/useActivity'
import {
  getDirectConversations,
  openDirectConversation,
} from '../api/conversations'
import { getFriends } from '../api/friendships'
import DirectConversationList from '../components/messages/DirectConversationList'
import { useRealtimeEvent } from '../realtime/useRealtime'
import type { MessageCreatedPayload } from '../realtime/messageEvents'

import type { DirectConversation } from '../types/conversations'
import type { PublicUser } from '../types/users'


type PageData = {
  conversations: DirectConversation[]
  friends: PublicUser[]
}


async function loadPageData(): Promise<PageData> {
  const [
    conversations,
    friends,
  ] = await Promise.all([
    getDirectConversations(),
    getFriends(),
  ])

  return {
    conversations,
    friends,
  }
}


function describeError(
  error: unknown,
): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Your session is not authenticated. Please sign in again.'
    }

    if (error.status === 404) {
      return 'The conversation could not be found.'
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}


function ConversationsPage() {
  const navigate = useNavigate()
  const activeConversationMatch =
    useMatch(
      '/messages/dm/:conversationId',
    )

  const { getDirectUnread } =
    useActivity()

  const [conversations, setConversations] =
    useState<DirectConversation[]>([])

  const [friends, setFriends] =
    useState<PublicUser[]>([])

  const [loading, setLoading] =
    useState(true)

  const [pageError, setPageError] =
    useState<string | null>(null)

  const [actionError, setActionError] =
    useState<string | null>(null)

  const [openingUserId, setOpeningUserId] =
    useState<number | null>(null)

  const refreshConversations =
    useCallback(async () => {
      setConversations(
        await getDirectConversations(),
      )
    }, [])

  const handleMessageCreated =
    useCallback(
      ({ payload }: {
        payload: MessageCreatedPayload
      }) => {
        if (
          payload.conversation_type
          === 'dm'
        ) {
          void refreshConversations()
        }
      },
      [refreshConversations],
    )

  useRealtimeEvent(
    'message.created',
    handleMessageCreated,
  )

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data =
          await loadPageData()

        if (cancelled) {
          return
        }

        setConversations(
          data.conversations,
        )
        setFriends(data.friends)
      } catch (error) {
        if (!cancelled) {
          setPageError(
            describeError(error),
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
  }, [])

  async function handleOpenConversation(
    friend: PublicUser,
  ) {
    setOpeningUserId(friend.id)
    setActionError(null)

    try {
      const conversation =
        await openDirectConversation(
          friend.id,
        )

      setConversations(
        (current) => {
          if (
            current.some(
              (item) =>
                item.id === conversation.id,
            )
          ) {
            return current
          }

          return [
            conversation,
            ...current,
          ]
        },
      )

      navigate(
        `/messages/dm/${conversation.id}`,
      )
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setOpeningUserId(null)
    }
  }

  if (loading) {
    return (
      <div className="dm-page-loading">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading direct messages"
        />
      </div>
    )
  }

  if (pageError) {
    return (
      <section>
        <h1 className="h2 mb-3">
          Direct Messages
        </h1>

        <div className="alert alert-danger">
          {pageError}
        </div>
      </section>
    )
  }

  const existingUserIds = new Set(
    conversations.map(
      (conversation) =>
        conversation.other_user.id,
    ),
  )

  const friendsWithoutConversation =
    friends.filter(
      (friend) =>
        !existingUserIds.has(friend.id),
    )

  return (
    <section
      className={`direct-messages-page${activeConversationMatch ? ' has-active-conversation' : ''}`}
    >
      <aside
        className="direct-messages-list-pane"
        aria-label="Direct message conversations"
      >
        <DirectConversationList
          conversations={conversations}
          friendsWithoutConversation={friendsWithoutConversation}
          friendCount={friends.length}
          getUnread={getDirectUnread}
          openingUserId={openingUserId}
          actionError={actionError}
          onOpenFriend={handleOpenConversation}
        />
      </aside>

      <div className="direct-messages-content-pane">
        <Outlet />
      </div>
    </section>
  )
}


export default ConversationsPage
