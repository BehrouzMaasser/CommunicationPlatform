import {
  useMemo,
  useState,
} from 'react'
import {
  Link,
  NavLink,
} from 'react-router-dom'

import {
  useRealtime,
} from '../../realtime/RealtimeContext'
import type {
  DirectConversation,
} from '../../types/conversations'
import type {
  PublicUser,
} from '../../types/users'

import Avatar from '../users/Avatar'


type DirectConversationListProps = {
  conversations: DirectConversation[]
  friendsWithoutConversation: PublicUser[]
  friendCount: number
  getUnread: (
    conversationId: number,
  ) => number
  openingUserId: number | null
  actionError: string | null
  onOpenFriend: (
    friend: PublicUser,
  ) => Promise<void>
}


function formatActivity(
  value: string,
): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate()

  if (sameDay) {
    return new Intl.DateTimeFormat(
      undefined,
      {
        hour: 'numeric',
        minute: '2-digit',
      },
    ).format(date)
  }

  return new Intl.DateTimeFormat(
    undefined,
    date.getFullYear() === now.getFullYear()
      ? {
          month: 'short',
          day: 'numeric',
        }
      : {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
        },
  ).format(date)
}


function DirectConversationList({
  conversations,
  friendsWithoutConversation,
  friendCount,
  getUnread,
  openingUserId,
  actionError,
  onOpenFriend,
}: DirectConversationListProps) {
  const {
    isUserOnline,
  } = useRealtime()

  const [searchQuery, setSearchQuery] =
    useState('')

  const [newMessageOpen, setNewMessageOpen] =
    useState(false)

  const normalizedQuery =
    searchQuery
      .trim()
      .toLocaleLowerCase()

  const filteredConversations =
    useMemo(
      () => {
        if (!normalizedQuery) {
          return conversations
        }

        return conversations.filter(
          (conversation) =>
            conversation
              .other_user
              .username
              .toLocaleLowerCase()
              .includes(
                normalizedQuery,
              ),
        )
      },
      [
        conversations,
        normalizedQuery,
      ],
    )

  const filteredNewMessageFriends =
    useMemo(
      () => {
        if (!normalizedQuery) {
          return friendsWithoutConversation
        }

        return friendsWithoutConversation.filter(
          (friend) =>
            friend.username
              .toLocaleLowerCase()
              .includes(
                normalizedQuery,
              ),
        )
      },
      [
        friendsWithoutConversation,
        normalizedQuery,
      ],
    )

  return (
    <div className="dm-list-shell">
      <div className="dm-list-header">
        <div className="min-width-0">
          <h1 className="dm-list-title mb-0">
            Direct Messages
          </h1>
          <div className="dm-list-subtitle">
            {conversations.length}{' '}
            {conversations.length === 1
              ? 'conversation'
              : 'conversations'}
          </div>
        </div>

        <button
          className={`dm-new-message-button${newMessageOpen ? ' is-active' : ''}`}
          type="button"
          aria-label={
            newMessageOpen
              ? 'Close new message panel'
              : 'Start a new direct message'
          }
          aria-expanded={newMessageOpen}
          title="New direct message"
          onClick={() => {
            setNewMessageOpen(
              (current) => !current,
            )
          }}
        >
          <span aria-hidden="true">
            {newMessageOpen ? '×' : '+'}
          </span>
        </button>
      </div>

      <div className="dm-list-search-wrap">
        <label
          className="visually-hidden"
          htmlFor="dm-conversation-search"
        >
          Search direct messages
        </label>
        <input
          id="dm-conversation-search"
          className="form-control dm-list-search"
          type="search"
          value={searchQuery}
          placeholder="Search people"
          autoComplete="off"
          onChange={(event) => {
            setSearchQuery(
              event.target.value,
            )
          }}
        />
      </div>

      {actionError && (
        <div
          className="alert alert-danger py-2 mx-3 mt-2 mb-0 small"
          role="alert"
        >
          {actionError}
        </div>
      )}

      {newMessageOpen && (
        <section
          className="dm-new-message-panel"
          aria-label="Start a new direct message"
        >
          <div className="dm-new-message-heading">
            Friends
          </div>

          {friendCount === 0 ? (
            <div className="dm-new-message-empty">
              <p className="mb-2">
                Add a friend before starting a direct message.
              </p>
              <Link
                className="btn btn-sm btn-outline-primary"
                to="/friends"
              >
                Find friends
              </Link>
            </div>
          ) : friendsWithoutConversation.length === 0 ? (
            <p className="dm-new-message-empty mb-0">
              You already have a conversation with every current friend.
            </p>
          ) : filteredNewMessageFriends.length === 0 ? (
            <p className="dm-new-message-empty mb-0">
              No friends match your search.
            </p>
          ) : (
            <div className="dm-new-message-list">
              {filteredNewMessageFriends.map(
                (friend) => (
                  <button
                    className="dm-new-message-person"
                    type="button"
                    key={friend.id}
                    disabled={
                      openingUserId !== null
                    }
                    onClick={() => {
                      void onOpenFriend(
                        friend,
                      )
                    }}
                  >
                    <Avatar
                      user={friend}
                      size="sm"
                      alt=""
                    />

                    <span className="dm-new-message-person-name">
                      @{friend.username}
                    </span>

                    <span className="dm-new-message-person-action">
                      {openingUserId === friend.id
                        ? 'Opening…'
                        : 'Message'}
                    </span>
                  </button>
                ),
              )}
            </div>
          )}
        </section>
      )}

      <div className="dm-conversation-list" role="list">
        {conversations.length === 0 ? (
          <div className="dm-list-empty">
            <div className="dm-list-empty-icon" aria-hidden="true">
              ✉
            </div>
            <div className="fw-semibold">
              No direct messages yet
            </div>
            <p className="small text-secondary mb-0">
              Use the + button to start one with a friend.
            </p>
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="dm-list-empty">
            <div className="fw-semibold">
              No matches
            </div>
            <p className="small text-secondary mb-0">
              Try a different username.
            </p>
          </div>
        ) : (
          filteredConversations.map(
            (conversation) => {
              const unread =
                getUnread(
                  conversation.id,
                )

              const online =
                isUserOnline(
                  conversation
                    .other_user
                    .id,
                )

              return (
                <NavLink
                  className={({ isActive }) =>
                    `dm-conversation-list-item${isActive ? ' active' : ''}`
                  }
                  key={conversation.id}
                  to={`/messages/dm/${conversation.id}`}
                  role="listitem"
                >
                  <span className="dm-conversation-avatar-wrap">
                    <Avatar
                      user={
                        conversation.other_user
                      }
                      size="md"
                      alt=""
                    />
                    <span
                      className={`dm-presence-dot${online ? ' is-online' : ''}`}
                      title={online ? 'Online' : 'Offline'}
                      aria-hidden="true"
                    />
                  </span>

                  <span className="dm-conversation-copy">
                    <span className="dm-conversation-row-top">
                      <span className="dm-conversation-name">
                        @{conversation.other_user.username}
                      </span>
                      <span className="dm-conversation-time">
                        {formatActivity(
                          conversation.last_activity_at,
                        )}
                      </span>
                    </span>

                    <span className="dm-conversation-row-bottom">
                      {online && (
                        <span className="dm-conversation-state">
                          Online
                        </span>
                      )}

                      {unread > 0 && (
                        <span
                          className="dm-unread-badge"
                          aria-label={`${unread} unread messages`}
                        >
                          {unread > 99
                            ? '99+'
                            : unread}
                        </span>
                      )}
                    </span>
                  </span>
                </NavLink>
              )
            },
          )
        )}
      </div>
    </div>
  )
}


export default DirectConversationList
