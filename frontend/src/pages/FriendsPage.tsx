import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useCallback,
  useEffect,
  useState,
} from 'react'

import { ApiError } from '../api/client'
import { useActivity } from '../activity/useActivity'
import {
  acceptFriendRequest,
  cancelFriendRequest,
  getFriends,
  getIncomingFriendRequests,
  getOutgoingFriendRequests,
  rejectFriendRequest,
  sendFriendRequest,
  unfriend,
} from '../api/friendships'
import { searchUsers } from '../api/users'
import Avatar from '../components/users/Avatar'
import {
  useRealtime,
  useRealtimeEvent,
} from '../realtime/RealtimeContext'

import type { FriendRequest } from '../types/friendships'
import type { PublicUser } from '../types/users'

type FriendshipData = {
  friends: PublicUser[]
  incoming: FriendRequest[]
  outgoing: FriendRequest[]
}

async function loadFriendshipData():
Promise<FriendshipData> {
  const [
    friends,
    incoming,
    outgoing,
  ] = await Promise.all([
    getFriends(),
    getIncomingFriendRequests(),
    getOutgoingFriendRequests(),
  ])

  return {
    friends,
    incoming,
    outgoing,
  }
}

function submitOnEnter(
  event: ReactKeyboardEvent<HTMLInputElement>,
) {
  if (
    event.key !== 'Enter'
    || event.nativeEvent.isComposing
    || event.shiftKey
    || event.altKey
    || event.ctrlKey
    || event.metaKey
  ) {
    return
  }

  const form = event.currentTarget.form
  const submitButton =
    form?.querySelector<HTMLButtonElement>(
      'button[type="submit"]',
    )

  if (!form || submitButton?.disabled) {
    return
  }

  event.preventDefault()
  form.requestSubmit()
}


function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'Your session is not authenticated. Please sign in again.'
    }

    if (error.status === 403) {
      return 'The server rejected this action.'
    }

    if (error.status === 404) {
      return 'The requested user or friendship could not be found.'
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}

function FriendsPage() {
  const { refreshActivity } =
    useActivity()

  const [friends, setFriends] =
    useState<PublicUser[]>([])
  const [incoming, setIncoming] =
    useState<FriendRequest[]>([])
  const [outgoing, setOutgoing] =
    useState<FriendRequest[]>([])

  const [loading, setLoading] =
    useState(true)
  const [pageError, setPageError] =
    useState<string | null>(null)
  const [actionError, setActionError] =
    useState<string | null>(null)

  const [searchText, setSearchText] =
    useState('')
  const [searchResults, setSearchResults] =
    useState<PublicUser[]>([])
  const [hasSearched, setHasSearched] =
    useState(false)
  const [searching, setSearching] =
    useState(false)

  const [busyAction, setBusyAction] =
    useState<string | null>(null)

  const applyData =
    useCallback(
      (data: FriendshipData) => {
        setFriends(data.friends)
        setIncoming(data.incoming)
        setOutgoing(data.outgoing)
      },
      [],
    )

  const refreshData =
    useCallback(
      async () => {
        const data =
          await loadFriendshipData()

        applyData(data)
      },
      [applyData],
    )

  const handleRealtimeChange =
    useCallback(
      () => {
        void refreshData()
      },
      [refreshData],
    )

  useRealtimeEvent(
    'friend_request.created',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'friend_request.accepted',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'friend_request.rejected',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'friend_request.cancelled',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'friendship.removed',
    handleRealtimeChange,
  )

  useEffect(() => {
    let cancelled = false

    async function loadPage() {
      try {
        const data =
          await loadFriendshipData()

        if (!cancelled) {
          applyData(data)
        }
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

    void loadPage()

    return () => {
      cancelled = true
    }
  }, [applyData])

  async function runAction(
    key: string,
    action: () => Promise<unknown>,
  ) {
    setBusyAction(key)
    setActionError(null)

    try {
      await action()
      await Promise.all([
        refreshData(),
        refreshActivity(),
      ])
    } catch (error) {
      setActionError(
        describeError(error),
      )
    } finally {
      setBusyAction(null)
    }
  }

  async function handleSearch(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const query = searchText.trim()

    if (!query) {
      setSearchResults([])
      setHasSearched(false)
      return
    }

    setSearching(true)
    setActionError(null)

    try {
      const users =
        await searchUsers(query)

      setSearchResults(users)
      setHasSearched(true)
    } catch (error) {
      setSearchResults([])
      setHasSearched(true)
      setActionError(
        describeError(error),
      )
    } finally {
      setSearching(false)
    }
  }

  async function handleAddFriend(
    user: PublicUser,
  ) {
    await runAction(
      `send-${user.id}`,
      () => sendFriendRequest(user.id),
    )

    setSearchResults((current) =>
      current.filter(
        (item) => item.id !== user.id,
      ),
    )
  }

  if (loading) {
    return (
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading friends"
        />
      </div>
    )
  }

  if (pageError) {
    return (
      <section>
        <h1 className="h2 mb-3">
          Friends
        </h1>

        <div className="alert alert-danger">
          {pageError}
        </div>
      </section>
    )
  }

  return (
    <section className="friends-page">
      <div className="directory-page-header">
        <div>
          <h1 className="directory-page-title mb-1">
            Friends
          </h1>
          <p className="directory-page-subtitle mb-0">
            Keep up with friends and manage connection requests.
          </p>
        </div>

        <span className="directory-count-pill">
          {friends.length}{' '}
          {friends.length === 1
            ? 'friend'
            : 'friends'}
        </span>
      </div>

      {actionError && (
        <div className="alert alert-danger">
          {actionError}
        </div>
      )}

      <div className="friends-layout">
        <div className="friends-primary-column">
          <section className="directory-surface">
            <div className="directory-section-header">
              <div>
                <h2 className="directory-section-title">
                  Your friends
                </h2>
                <p className="directory-section-subtitle mb-0">
                  People you can message and see online.
                </p>
              </div>
            </div>

            {friends.length === 0 ? (
              <DirectoryEmpty
                title="No friends yet"
                text="Search for someone by username to send your first request."
              />
            ) : (
              <div className="directory-list">
                {friends.map((friend) => {
                  const key =
                    `unfriend-${friend.id}`

                  return (
                    <div
                      className="directory-list-row"
                      key={friend.id}
                    >
                      <UserIdentity
                        user={friend}
                        showPresence
                        size="md"
                      />

                      <button
                        className="btn btn-sm btn-outline-danger directory-row-action"
                        type="button"
                        disabled={busyAction !== null}
                        onClick={() =>
                          void runAction(
                            key,
                            () =>
                              unfriend(
                                friend.id,
                              ),
                          )
                        }
                      >
                        {busyAction === key
                          ? 'Removing…'
                          : 'Unfriend'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        </div>

        <div className="friends-secondary-column">
          <section className="directory-surface">
            <div className="directory-section-header">
              <div>
                <h2 className="directory-section-title">
                  Find people
                </h2>
                <p className="directory-section-subtitle mb-0">
                  Search by exact or partial username.
                </p>
              </div>
            </div>

            <form
              className="directory-search-form"
              onSubmit={handleSearch}
            >
              <input
                className="form-control directory-search-input"
                type="search"
                value={searchText}
                onChange={(event) =>
                  setSearchText(
                    event.target.value,
                  )
                }
                onKeyDown={submitOnEnter}
                placeholder="Search usernames"
                aria-label="Search by username"
              />

              <button
                className="btn btn-primary"
                type="submit"
                disabled={
                  searching
                  || !searchText.trim()
                }
              >
                {searching
                  ? 'Searching…'
                  : 'Search'}
              </button>
            </form>

            {hasSearched && (
              <div className="directory-search-results">
                {searchResults.length === 0 ? (
                  <p className="small text-secondary mb-0 py-2">
                    No users found.
                  </p>
                ) : (
                  <div className="directory-list directory-list-compact">
                    {searchResults.map(
                      (user) => {
                        const key =
                          `send-${user.id}`

                        return (
                          <div
                            className="directory-list-row"
                            key={user.id}
                          >
                            <UserIdentity
                              user={user}
                              size="sm"
                            />

                            <button
                              className="btn btn-sm btn-primary directory-row-action"
                              type="button"
                              disabled={busyAction !== null}
                              onClick={() =>
                                void handleAddFriend(
                                  user,
                                )
                              }
                            >
                              {busyAction === key
                                ? 'Sending…'
                                : 'Add'}
                            </button>
                          </div>
                        )
                      },
                    )}
                  </div>
                )}
              </div>
            )}
          </section>

          <section className="directory-surface">
            <div className="directory-section-header">
              <div>
                <h2 className="directory-section-title">
                  Incoming requests
                </h2>
                <p className="directory-section-subtitle mb-0">
                  {incoming.length === 0
                    ? 'Nothing waiting for you.'
                    : `${incoming.length} waiting for your response.`}
                </p>
              </div>

              {incoming.length > 0 && (
                <span className="directory-section-count">
                  {incoming.length}
                </span>
              )}
            </div>

            {incoming.length === 0 ? (
              <DirectoryEmpty
                compact
                title="No incoming requests"
              />
            ) : (
              <div className="directory-list directory-list-compact">
                {incoming.map((request) => {
                  const acceptKey =
                    `accept-${request.id}`
                  const rejectKey =
                    `reject-${request.id}`

                  return (
                    <div
                      className="directory-request-row"
                      key={request.id}
                    >
                      <UserIdentity
                        user={request.sender}
                        size="sm"
                      />

                      <div className="directory-request-actions">
                        <button
                          className="btn btn-sm btn-primary"
                          type="button"
                          disabled={busyAction !== null}
                          onClick={() =>
                            void runAction(
                              acceptKey,
                              () =>
                                acceptFriendRequest(
                                  request.id,
                                ),
                            )
                          }
                        >
                          {busyAction === acceptKey
                            ? 'Accepting…'
                            : 'Accept'}
                        </button>

                        <button
                          className="btn btn-sm btn-outline-secondary"
                          type="button"
                          disabled={busyAction !== null}
                          onClick={() =>
                            void runAction(
                              rejectKey,
                              () =>
                                rejectFriendRequest(
                                  request.id,
                                ),
                            )
                          }
                        >
                          {busyAction === rejectKey
                            ? 'Rejecting…'
                            : 'Reject'}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </section>

          <section className="directory-surface">
            <div className="directory-section-header">
              <div>
                <h2 className="directory-section-title">
                  Sent requests
                </h2>
                <p className="directory-section-subtitle mb-0">
                  Requests waiting for someone else.
                </p>
              </div>

              {outgoing.length > 0 && (
                <span className="directory-section-count">
                  {outgoing.length}
                </span>
              )}
            </div>

            {outgoing.length === 0 ? (
              <DirectoryEmpty
                compact
                title="No sent requests"
              />
            ) : (
              <div className="directory-list directory-list-compact">
                {outgoing.map((request) => {
                  const key =
                    `cancel-${request.id}`

                  return (
                    <div
                      className="directory-list-row"
                      key={request.id}
                    >
                      <UserIdentity
                        user={request.recipient}
                        size="sm"
                      />

                      <button
                        className="btn btn-sm btn-outline-secondary directory-row-action"
                        type="button"
                        disabled={busyAction !== null}
                        onClick={() =>
                          void runAction(
                            key,
                            () =>
                              cancelFriendRequest(
                                request.id,
                              ),
                          )
                        }
                      >
                        {busyAction === key
                          ? 'Cancelling…'
                          : 'Cancel'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </section>
  )
}

function DirectoryEmpty({
  title,
  text,
  compact = false,
}: {
  title: string
  text?: string
  compact?: boolean
}) {
  return (
    <div
      className={
        `directory-empty${compact ? ' directory-empty-compact' : ''}`
      }
    >
      <div className="fw-semibold">
        {title}
      </div>
      {text && (
        <p className="small text-secondary mb-0">
          {text}
        </p>
      )}
    </div>
  )
}

function UserIdentity({
  user,
  showPresence = false,
  size = 'md',
}: {
  user: PublicUser
  showPresence?: boolean
  size?: 'sm' | 'md'
}) {
  const {
    isUserOnline,
  } = useRealtime()

  const online =
    showPresence
    && isUserOnline(user.id)

  return (
    <div className="directory-user-identity">
      <span className="directory-user-avatar-wrap">
        <Avatar
          user={user}
          size={size}
          alt=""
        />
        {showPresence && (
          <span
            className={`directory-presence-dot${online ? ' is-online' : ''}`}
            title={online ? 'Online' : 'Offline'}
            aria-hidden="true"
          />
        )}
      </span>

      <span className="directory-user-copy">
        <span className="directory-user-name">
          @{user.username}
        </span>
        {showPresence && online && (
          <span className="directory-user-state">
            Online
          </span>
        )}
      </span>
    </div>
  )
}

export default FriendsPage
