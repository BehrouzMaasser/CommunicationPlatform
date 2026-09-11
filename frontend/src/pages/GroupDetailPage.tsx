import {
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  Link,
  useNavigate,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { getFriends } from '../api/friendships'
import {
  createGroupInvitationLink,
  disbandGroup,
  getGroup,
  getGroupMembers,
  inviteUserToGroup,
  leaveGroup,
  removeGroupMember,
  renameGroup,
  revokeGroupInvitationLink,
} from '../api/groups'
import { getCurrentUser } from '../api/session'

import type {
  GroupConversation,
  GroupInvitationLink,
  GroupMembership,
} from '../types/groups'
import type {
  CurrentUser,
  PublicUser,
} from '../types/users'

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}

function GroupDetailPage() {
  const { groupId } =
    useParams<{ groupId: string }>()

  const navigate = useNavigate()
  const parsedGroupId = Number(groupId)

  const [group, setGroup] =
    useState<GroupConversation | null>(null)
  const [members, setMembers] =
    useState<GroupMembership[]>([])
  const [friends, setFriends] =
    useState<PublicUser[]>([])
  const [currentUser, setCurrentUser] =
    useState<CurrentUser | null>(null)

  const [renameText, setRenameText] =
    useState('')
  const [busy, setBusy] =
    useState<string | null>(null)
  const [error, setError] =
    useState<string | null>(null)
  const [notice, setNotice] =
    useState<string | null>(null)
  const [loading, setLoading] =
    useState(true)
  const [invitedUserIds, setInvitedUserIds] =
    useState<Set<number>>(
      () => new Set(),
    )
  const [link, setLink] =
    useState<GroupInvitationLink | null>(
      null,
    )

  async function refreshMembers() {
    setMembers(
      await getGroupMembers(
        parsedGroupId,
      ),
    )
  }

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (
        !Number.isInteger(parsedGroupId) ||
        parsedGroupId <= 0
      ) {
        setError('Invalid group id.')
        setLoading(false)
        return
      }

      try {
        const [
          groupResult,
          memberResult,
          friendResult,
          userResult,
        ] = await Promise.all([
          getGroup(parsedGroupId),
          getGroupMembers(
            parsedGroupId,
          ),
          getFriends(),
          getCurrentUser(),
        ])

        if (cancelled) {
          return
        }

        setGroup(groupResult)
        setMembers(memberResult)
        setFriends(friendResult)
        setCurrentUser(userResult)
        setRenameText(
          groupResult.name,
        )
      } catch (requestError) {
        if (!cancelled) {
          setError(
            errorText(requestError),
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

  const currentMembership =
    members.find(
      (membership) =>
        membership.user.id ===
        currentUser?.id,
    )

  const isOwner =
    currentMembership?.role === 'OWNER'

  const memberIds = useMemo(
    () =>
      new Set(
        members.map(
          (membership) =>
            membership.user.id,
        ),
      ),
    [members],
  )

  const inviteCandidates =
    friends.filter(
      (friend) =>
        !memberIds.has(friend.id),
    )

  async function handleRename(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (!renameText.trim()) {
      return
    }

    setBusy('rename')
    setError(null)
    setNotice(null)

    try {
      const updated =
        await renameGroup(
          parsedGroupId,
          renameText,
        )

      setGroup(updated)
      setRenameText(updated.name)
      setNotice('Group renamed.')
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  async function handleInvite(
    friend: PublicUser,
  ) {
    const key = `invite-${friend.id}`
    setBusy(key)
    setError(null)
    setNotice(null)

    try {
      await inviteUserToGroup(
        parsedGroupId,
        friend.id,
      )

      setInvitedUserIds(
        (current) =>
          new Set(current).add(
            friend.id,
          ),
      )

      setNotice(
        `Invitation sent to @${friend.username}.`,
      )
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  async function handleRemove(
    membership: GroupMembership,
  ) {
    setBusy(
      `remove-${membership.user.id}`,
    )
    setError(null)
    setNotice(null)

    try {
      await removeGroupMember(
        parsedGroupId,
        membership.user.id,
      )
      await refreshMembers()
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  async function handleLeave() {
    setBusy('leave')
    setError(null)

    try {
      await leaveGroup(
        parsedGroupId,
      )
      navigate('/groups')
    } catch (requestError) {
      setError(errorText(requestError))
      setBusy(null)
    }
  }

  async function handleDisband() {
    if (
      !window.confirm(
        'Disband this group? This cannot be undone.',
      )
    ) {
      return
    }

    setBusy('disband')
    setError(null)

    try {
      await disbandGroup(
        parsedGroupId,
      )
      navigate('/groups')
    } catch (requestError) {
      setError(errorText(requestError))
      setBusy(null)
    }
  }

  async function handleCreateLink() {
    setBusy('link')
    setError(null)
    setNotice(null)

    try {
      const result =
        await createGroupInvitationLink(
          parsedGroupId,
        )
      setLink(result)
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  async function handleRevokeLink() {
    if (!link) {
      return
    }

    setBusy('revoke-link')
    setError(null)

    try {
      await revokeGroupInvitationLink(
        parsedGroupId,
        link.id,
      )
      setLink(null)
      setNotice(
        'Invitation link revoked.',
      )
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

  if (error && !group) {
    return (
      <section>
        <Link to="/groups">
          ← Back to groups
        </Link>
        <div className="alert alert-danger mt-3">
          {error}
        </div>
      </section>
    )
  }

  if (!group) {
    return null
  }

  const joinUrl = link
    ? `${window.location.origin}/groups/join/${link.token}`
    : null

  return (
    <section>
      <Link
        className="btn btn-link px-0 mb-3"
        to="/groups"
      >
        ← Back to groups
      </Link>

      <div className="d-flex justify-content-between align-items-start gap-3 mb-4">
        <div>
          <h1 className="h2 mb-1">
            {group.name}
          </h1>
          <div className="text-secondary">
            Group #{group.id}
          </div>
        </div>

        {isOwner ? (
          <button
            className="btn btn-outline-danger"
            disabled={busy !== null}
            onClick={() =>
              void handleDisband()
            }
          >
            Disband
          </button>
        ) : (
          <button
            className="btn btn-outline-danger"
            disabled={busy !== null}
            onClick={() =>
              void handleLeave()
            }
          >
            Leave group
          </button>
        )}
      </div>

      {error && (
        <div className="alert alert-danger">
          {error}
        </div>
      )}

      {notice && (
        <div className="alert alert-success">
          {notice}
        </div>
      )}

      {isOwner && (
        <div className="card shadow-sm mb-4">
          <div className="card-body">
            <h2 className="h5">
              Group settings
            </h2>

            <form
              className="d-flex gap-2"
              onSubmit={handleRename}
            >
              <input
                className="form-control"
                value={renameText}
                onChange={(event) =>
                  setRenameText(
                    event.target.value,
                  )
                }
              />
              <button
                className="btn btn-primary"
                disabled={
                  busy !== null ||
                  !renameText.trim()
                }
              >
                Rename
              </button>
            </form>
          </div>
        </div>
      )}

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card shadow-sm h-100">
            <div className="card-body">
              <h2 className="h5 mb-3">
                Members
              </h2>

              <div className="list-group list-group-flush">
                {members.map(
                  (membership) => (
                    <div
                      className="list-group-item px-0 d-flex justify-content-between align-items-center gap-3"
                      key={membership.user.id}
                    >
                      <div>
                        <div className="fw-semibold">
                          @{membership.user.username}
                        </div>
                        <div className="small text-secondary">
                          {membership.role}
                        </div>
                      </div>

                      {isOwner &&
                        membership.role !== 'OWNER' && (
                          <button
                            className="btn btn-sm btn-outline-danger"
                            disabled={busy !== null}
                            onClick={() =>
                              void handleRemove(
                                membership,
                              )
                            }
                          >
                            Remove
                          </button>
                        )}
                    </div>
                  ),
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="col-lg-5">
          {isOwner && (
            <>
              <div className="card shadow-sm mb-4">
                <div className="card-body">
                  <h2 className="h5 mb-3">
                    Invite a friend
                  </h2>

                  {inviteCandidates.length === 0 ? (
                    <p className="text-secondary mb-0">
                      No current friends available to invite.
                    </p>
                  ) : (
                    <div className="list-group list-group-flush">
                      {inviteCandidates.map(
                        (friend) => (
                          <div
                            className="list-group-item px-0 d-flex justify-content-between align-items-center gap-3"
                            key={friend.id}
                          >
                            <span>
                              @{friend.username}
                            </span>

                            <button
                              className="btn btn-sm btn-primary"
                              disabled={
                                busy !== null ||
                                invitedUserIds.has(
                                  friend.id,
                                )
                              }
                              onClick={() =>
                                void handleInvite(
                                  friend,
                                )
                              }
                            >
                              {invitedUserIds.has(
                                friend.id,
                              )
                                ? 'Invited'
                                : 'Invite'}
                            </button>
                          </div>
                        ),
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="card shadow-sm">
                <div className="card-body">
                  <h2 className="h5">
                    Invitation link
                  </h2>

                  {!link ? (
                    <button
                      className="btn btn-outline-primary"
                      disabled={busy !== null}
                      onClick={() =>
                        void handleCreateLink()
                      }
                    >
                      Create link
                    </button>
                  ) : (
                    <>
                      <input
                        className="form-control mb-2"
                        readOnly
                        value={joinUrl ?? ''}
                      />

                      <div className="small text-secondary mb-3">
                        Expires:{' '}
                        {new Date(
                          link.expires_at,
                        ).toLocaleString()}
                      </div>

                      <button
                        className="btn btn-outline-danger btn-sm"
                        disabled={busy !== null}
                        onClick={() =>
                          void handleRevokeLink()
                        }
                      >
                        Revoke link
                      </button>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  )
}

export default GroupDetailPage
