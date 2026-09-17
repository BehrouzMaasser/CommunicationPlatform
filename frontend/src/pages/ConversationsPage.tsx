import {
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Link,
  useNavigate,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { useActivity } from '../activity/useActivity'
import {
  getDirectConversations,
  openDirectConversation,
} from '../api/conversations'
import { getFriends } from '../api/friendships'
import { useRealtimeEvent } from '../realtime/RealtimeContext'
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

function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Your session is not authenticated. Please sign in again.'
    }

    if (error.status === 404) {
      return 'The conversation could not be found.'
    }

    if (error.status === 400) {
      return error.message
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}

function formatActivity(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: 'medium',
      timeStyle: 'short',
    },
  ).format(date)
}

function ConversationsPage() {
  const navigate = useNavigate()
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
        const data = await loadPageData()

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
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading conversations"
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
    <section>
      <div className="mb-4">
        <h1 className="h2 mb-1">
          Direct Messages
        </h1>
        <p className="text-secondary mb-0">
          Open an existing direct conversation
          or start one with a friend.
        </p>
      </div>

      {actionError && (
        <div className="alert alert-danger">
          {actionError}
        </div>
      )}

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card shadow-sm">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h2 className="h5 mb-0">
                  Direct messages
                </h2>

                <span className="badge text-bg-secondary">
                  {conversations.length}
                </span>
              </div>

              {conversations.length === 0 ? (
                <p className="text-secondary mb-0">
                  No direct conversations yet.
                </p>
              ) : (
                <div className="list-group">
                  {conversations.map(
                    (conversation) => (
                      <Link
                        className="list-group-item list-group-item-action d-flex justify-content-between align-items-center gap-3"
                        key={conversation.id}
                        to={`/messages/dm/${conversation.id}`}
                      >
                        <div>
                          <div className="fw-semibold">
                            @{conversation.other_user.username}
                          </div>
                        </div>

                        <div className="d-flex align-items-center gap-3">
                          {getDirectUnread(
                            conversation.id,
                          ) > 0 && (
                            <span
                              className="unread-count-badge"
                              title={`${getDirectUnread(conversation.id)} unread messages`}
                            >
                              {getDirectUnread(
                                conversation.id,
                              ) > 99
                                ? '99+'
                                : getDirectUnread(
                                    conversation.id,
                                  )}
                            </span>
                          )}

                          <div className="small text-secondary text-end">
                            <div>
                              Last activity
                            </div>
                            <div>
                              {formatActivity(
                                conversation.last_activity_at,
                              )}
                            </div>
                          </div>
                        </div>
                      </Link>
                    ),
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          <div className="card shadow-sm">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <h2 className="h5 mb-0">
                  Start a conversation
                </h2>

                <span className="badge text-bg-secondary">
                  {friendsWithoutConversation.length}
                </span>
              </div>

              {friends.length === 0 ? (
                <div>
                  <p className="text-secondary">
                    You need a friend before
                    starting a new direct message.
                  </p>

                  <Link
                    className="btn btn-outline-primary btn-sm"
                    to="/friends"
                  >
                    Find friends
                  </Link>
                </div>
              ) : friendsWithoutConversation.length === 0 ? (
                <p className="text-secondary mb-0">
                  You already have a direct conversation
                  with every current friend.
                </p>
              ) : (
                <div className="list-group list-group-flush">
                  {friendsWithoutConversation.map(
                    (friend) => (
                      <div
                        className="list-group-item px-0 d-flex justify-content-between align-items-center gap-3"
                        key={friend.id}
                      >
                        <div>
                          <div className="fw-semibold">
                            @{friend.username}
                          </div>
                        </div>

                        <button
                          className="btn btn-sm btn-primary"
                          type="button"
                          disabled={
                            openingUserId !== null
                          }
                          onClick={() =>
                            void handleOpenConversation(
                              friend,
                            )
                          }
                        >
                          {openingUserId === friend.id
                            ? 'Opening…'
                            : 'Message'}
                        </button>
                      </div>
                    ),
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default ConversationsPage
