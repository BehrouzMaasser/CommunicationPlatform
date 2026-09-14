import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
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
import { useRealtimeEvent } from '../realtime/RealtimeContext'
import type { MessageCreatedPayload } from '../realtime/messageEvents'
import {
  acceptGroupInvitation,
  createGroup,
  getGroups,
  getIncomingGroupInvitations,
  rejectGroupInvitation,
} from '../api/groups'

import type {
  GroupConversation,
  GroupInvitation,
} from '../types/groups'

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


function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}

function GroupsPage() {
  const navigate = useNavigate()
  const {
    getGroupUnread,
    refreshActivity,
  } = useActivity()

  const [groups, setGroups] =
    useState<GroupConversation[]>([])
  const [invitations, setInvitations] =
    useState<GroupInvitation[]>([])
  const [name, setName] = useState('')
  const [loading, setLoading] =
    useState(true)
  const [busy, setBusy] =
    useState<string | null>(null)
  const [error, setError] =
    useState<string | null>(null)

  const refresh =
    useCallback(
      async () => {
        const [
          groupData,
          invitationData,
        ] = await Promise.all([
          getGroups(),
          getIncomingGroupInvitations(),
        ])

        setGroups(groupData)
        setInvitations(
          invitationData,
        )
      },
      [],
    )

  const refreshGroups =
    useCallback(
      async () => {
        setGroups(
          await getGroups(),
        )
      },
      [],
    )

  const handleRealtimeChange =
    useCallback(
      () => {
        void refresh()
      },
      [refresh],
    )

  const handleMessageCreated =
    useCallback(
      ({ payload }: {
        payload: MessageCreatedPayload
      }) => {
        if (
          payload.conversation_type
          === 'group'
        ) {
          void refreshGroups()
        }
      },
      [refreshGroups],
    )

  useRealtimeEvent(
    'message.created',
    handleMessageCreated,
  )
  useRealtimeEvent(
    'group_invitation.created',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group_invitation.accepted',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group_invitation.rejected',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.member_added',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.member_removed',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.member_left',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.renamed',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.deleted',
    handleRealtimeChange,
  )

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [groupData, invitationData] =
          await Promise.all([
            getGroups(),
            getIncomingGroupInvitations(),
          ])

        if (!cancelled) {
          setGroups(groupData)
          setInvitations(invitationData)
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(errorText(requestError))
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

  async function handleCreate(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!name.trim()) {
      return
    }

    setBusy('create')
    setError(null)

    try {
      const group =
        await createGroup(name)

      setName('')
      navigate(`/groups/${group.id}`)
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  async function handleInvitation(
    invitationId: number,
    action: 'accept' | 'reject',
  ) {
    const key =
      `${action}-${invitationId}`

    setBusy(key)
    setError(null)

    try {
      if (action === 'accept') {
        await acceptGroupInvitation(
          invitationId,
        )
      } else {
        await rejectGroupInvitation(
          invitationId,
        )
      }

      await Promise.all([
        refresh(),
        refreshActivity(),
      ])
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  if (loading) {
    return (
      <div className="py-5 text-center">
        <div className="spinner-border" />
      </div>
    )
  }

  return (
    <section>
      <div className="mb-4">
        <h1 className="h2 mb-1">
          Groups
        </h1>
        <p className="text-secondary mb-0">
          Create groups and manage invitations.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h5">
            Create group
          </h2>

          <form
            className="d-flex gap-2"
            onSubmit={handleCreate}
          >
            <input
              className="form-control"
              value={name}
              onChange={(event) =>
                setName(event.target.value)
              }
              onKeyDown={submitOnEnter}
              placeholder="Group name"
            />

            <button
              className="btn btn-primary text-nowrap"
              type="submit"
              disabled={
                busy === 'create' ||
                !name.trim()
              }
            >
              {busy === 'create'
                ? 'Creating…'
                : 'Create'}
            </button>
          </form>
        </div>
      </div>

      {invitations.length > 0 && (
        <div className="card shadow-sm mb-4">
          <div className="card-body">
            <h2 className="h5 mb-3">
              Invitations
            </h2>

            <div className="list-group">
              {invitations.map(
                (invitation) => (
                  <div
                    className="list-group-item"
                    key={invitation.id}
                  >
                    <div className="d-flex flex-column flex-md-row justify-content-between gap-3">
                      <div>
                        <div className="fw-semibold">
                          {invitation.group.name}
                        </div>
                        <div className="small text-secondary">
                          Invited by @{invitation.invited_by.username}
                        </div>
                      </div>

                      <div className="d-flex gap-2">
                        <button
                          className="btn btn-sm btn-primary"
                          disabled={busy !== null}
                          onClick={() =>
                            void handleInvitation(
                              invitation.id,
                              'accept',
                            )
                          }
                        >
                          {busy ===
                          `accept-${invitation.id}`
                            ? 'Accepting…'
                            : 'Accept'}
                        </button>

                        <button
                          className="btn btn-sm btn-outline-secondary"
                          disabled={busy !== null}
                          onClick={() =>
                            void handleInvitation(
                              invitation.id,
                              'reject',
                            )
                          }
                        >
                          {busy ===
                          `reject-${invitation.id}`
                            ? 'Rejecting…'
                            : 'Reject'}
                        </button>
                      </div>
                    </div>
                  </div>
                ),
              )}
            </div>
          </div>
        </div>
      )}

      <div className="card shadow-sm">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h2 className="h5 mb-0">
              Your groups
            </h2>
            <span className="badge text-bg-secondary">
              {groups.length}
            </span>
          </div>

          {groups.length === 0 ? (
            <p className="text-secondary mb-0">
              You are not in any groups yet.
            </p>
          ) : (
            <div className="list-group">
              {groups.map((group) => (
                <Link
                  className="list-group-item list-group-item-action"
                  key={group.id}
                  to={`/groups/${group.id}`}
                >
                  <div className="d-flex justify-content-between align-items-center gap-3">
                    <div>
                      <div className="fw-semibold">
                        {group.name}
                      </div>
                    </div>

                    {getGroupUnread(
                      group.id,
                    ) > 0 && (
                      <span
                        className="unread-count-badge"
                        title={`${getGroupUnread(group.id)} unread messages`}
                      >
                        {getGroupUnread(
                          group.id,
                        ) > 99
                          ? '99+'
                          : getGroupUnread(
                              group.id,
                            )}
                      </span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

export default GroupsPage
