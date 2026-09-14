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
    <section>
      <div className="mb-4">
        <h1 className="h2 mb-1">
          Friends
        </h1>
        <p className="text-secondary mb-0">
          Find people by username and manage friendships.
        </p>
      </div>

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h5 mb-3">
            Find people
          </h2>

          <form
            className="d-flex gap-2"
            onSubmit={handleSearch}
          >
            <input
              className="form-control"
              type="search"
              value={searchText}
              onChange={(event) =>
                setSearchText(
                  event.target.value,
                )
              }
              onKeyDown={submitOnEnter}
              placeholder="Search by username"
              aria-label="Search by username"
            />

            <button
              className="btn btn-primary"
              type="submit"
              disabled={
                searching ||
                !searchText.trim()
              }
            >
              {searching
                ? 'Searching…'
                : 'Search'}
            </button>
          </form>

          {hasSearched && (
            <div className="mt-3">
              {searchResults.length === 0 ? (
                <p className="text-secondary mb-0">
                  No users found.
                </p>
              ) : (
                <div className="list-group">
                  {searchResults.map(
                    (user) => {
                      const key =
                        `send-${user.id}`

                      return (
                        <div
                          className="list-group-item d-flex justify-content-between align-items-center gap-3"
                          key={user.id}
                        >
                          <UserIdentity
                            user={user}
                          />

                          <button
                            className="btn btn-sm btn-primary"
                            type="button"
                            disabled={
                              busyAction !== null
                            }
                            onClick={() =>
                              void handleAddFriend(
                                user,
                              )
                            }
                          >
                            {busyAction === key
                              ? 'Sending…'
                              : 'Add friend'}
                          </button>
                        </div>
                      )
                    },
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {actionError && (
        <div className="alert alert-danger">
          {actionError}
        </div>
      )}

      <div className="row g-4">
        <div className="col-lg-4">
          <FriendCard
            title="Friends"
            count={friends.length}
          >
            {friends.length === 0 ? (
              <EmptyState text="No friends yet." />
            ) : (
              <div className="list-group list-group-flush">
                {friends.map((friend) => {
                  const key =
                    `unfriend-${friend.id}`

                  return (
                    <div
                      className="list-group-item px-0 d-flex justify-content-between align-items-center gap-3"
                      key={friend.id}
                    >
                      <UserIdentity
                        user={friend}
                        showPresence
                      />

                      <button
                        className="btn btn-sm btn-outline-danger"
                        type="button"
                        disabled={
                          busyAction !== null
                        }
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
          </FriendCard>
        </div>

        <div className="col-lg-4">
          <FriendCard
            title="Incoming"
            count={incoming.length}
          >
            {incoming.length === 0 ? (
              <EmptyState text="No incoming requests." />
            ) : (
              <div className="list-group list-group-flush">
                {incoming.map((request) => {
                  const acceptKey =
                    `accept-${request.id}`
                  const rejectKey =
                    `reject-${request.id}`

                  return (
                    <div
                      className="list-group-item px-0"
                      key={request.id}
                    >
                      <UserIdentity
                        user={request.sender}
                      />

                      <div className="d-flex gap-2 mt-3">
                        <button
                          className="btn btn-sm btn-primary"
                          type="button"
                          disabled={
                            busyAction !== null
                          }
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
                          {busyAction ===
                          acceptKey
                            ? 'Accepting…'
                            : 'Accept'}
                        </button>

                        <button
                          className="btn btn-sm btn-outline-secondary"
                          type="button"
                          disabled={
                            busyAction !== null
                          }
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
                          {busyAction ===
                          rejectKey
                            ? 'Rejecting…'
                            : 'Reject'}
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </FriendCard>
        </div>

        <div className="col-lg-4">
          <FriendCard
            title="Outgoing"
            count={outgoing.length}
          >
            {outgoing.length === 0 ? (
              <EmptyState text="No outgoing requests." />
            ) : (
              <div className="list-group list-group-flush">
                {outgoing.map((request) => {
                  const key =
                    `cancel-${request.id}`

                  return (
                    <div
                      className="list-group-item px-0 d-flex justify-content-between align-items-center gap-3"
                      key={request.id}
                    >
                      <UserIdentity
                        user={
                          request.recipient
                        }
                      />

                      <button
                        className="btn btn-sm btn-outline-secondary"
                        type="button"
                        disabled={
                          busyAction !== null
                        }
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
          </FriendCard>
        </div>
      </div>
    </section>
  )
}

type FriendCardProps = {
  title: string
  count: number
  children: React.ReactNode
}

function FriendCard({
  title,
  count,
  children,
}: FriendCardProps) {
  return (
    <div className="card shadow-sm h-100">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-3">
          <h2 className="h5 mb-0">
            {title}
          </h2>

          <span className="badge text-bg-secondary">
            {count}
          </span>
        </div>

        {children}
      </div>
    </div>
  )
}

function EmptyState({
  text,
}: {
  text: string
}) {
  return (
    <p className="text-secondary mb-0 py-2">
      {text}
    </p>
  )
}

function UserIdentity({
  user,
  showPresence = false,
}: {
  user: PublicUser
  showPresence?: boolean
}) {
  const {
    isUserOnline,
  } = useRealtime()

  const online =
    showPresence &&
    isUserOnline(user.id)
  return (
    <div>
      <div className="fw-semibold d-flex align-items-center gap-2">
        <span>
          @{user.username}
        </span>

        {showPresence && (
          <span
            className={
              online
                ? 'badge text-bg-success'
                : 'badge text-bg-secondary'
            }
          >
            {online
              ? 'Online'
              : 'Offline'}
          </span>
        )}
      </div>
    </div>
  )
}

export default FriendsPage
