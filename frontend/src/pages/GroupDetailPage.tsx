import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useCallback,
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
import { useActivity } from '../activity/useActivity'
import { getFriends } from '../api/friendships'
import {
  createGroupInvitationLink,
  disbandGroup,
  getActiveGroupInvitationLinks,
  getGroup,
  getGroupMembers,
  getGroupPendingInvitations,
  inviteUserToGroup,
  leaveGroup,
  removeGroupMember,
  renameGroup,
  revokeGroupInvitationLink,
} from '../api/groups'
import { getCurrentUser } from '../api/session'
import { useRealtimeEvent } from '../realtime/RealtimeContext'
import type {
  GroupInvitationEventPayload,
  GroupMemberEventPayload,
  GroupRenamedPayload,
} from '../realtime/groupEvents'

import type {
  GroupConversation,
  GroupInvitationLink,
  GroupInvitationLinkSummary,
  GroupMembership,
} from '../types/groups'
import type {
  CurrentUser,
  PublicUser,
} from '../types/users'

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

function GroupDetailPage() {
  const { groupId } =
    useParams<{ groupId: string }>()

  const navigate = useNavigate()
  const parsedGroupId = Number(groupId)
  const { getGroupUnread } =
    useActivity()

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
  const [showDisbandConfirm, setShowDisbandConfirm] =
    useState(false)
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
  const [
    activeInvitationLinks,
    setActiveInvitationLinks,
  ] = useState<GroupInvitationLinkSummary[]>(
    [],
  )

  const refreshGroupState =
    useCallback(
      async () => {
        const [
          groupResult,
          memberResult,
        ] = await Promise.all([
          getGroup(
            parsedGroupId,
          ),
          getGroupMembers(
            parsedGroupId,
          ),
        ])

        const currentMembership =
          memberResult.find(
            (membership) =>
              membership.user.id ===
              currentUser?.id,
          )

        const isCurrentUserOwner =
          currentMembership?.role ===
          'OWNER'

        const [
          pendingInvitationResult,
          activeInvitationLinkResult,
        ] = isCurrentUserOwner
          ? await Promise.all([
              getGroupPendingInvitations(
                parsedGroupId,
              ),
              getActiveGroupInvitationLinks(
                parsedGroupId,
              ),
            ])
          : [[], []]

        setGroup(groupResult)
        setMembers(memberResult)
        setInvitedUserIds(
          new Set(
            pendingInvitationResult.map(
              (invitation) =>
                invitation.recipient.id,
            ),
          ),
        )
        setActiveInvitationLinks(
          activeInvitationLinkResult,
        )
        setRenameText(
          groupResult.name,
        )
      },
      [
        currentUser?.id,
        parsedGroupId,
      ],
    )

  const refreshMembers =
    useCallback(
      async () => {
        setMembers(
          await getGroupMembers(
            parsedGroupId,
          ),
        )
      },
      [parsedGroupId],
    )

  const handleMemberChange =
    useCallback(
      ({
        payload,
      }: {
        payload:
          GroupMemberEventPayload
      }) => {
        if (
          payload.group_id !==
          parsedGroupId
        ) {
          return
        }

        setInvitedUserIds(
          (current) => {
            const next =
              new Set(current)
            next.delete(
              payload.user_id,
            )
            return next
          },
        )

        if (
          payload.user_id ===
          currentUser?.id
        ) {
          void getGroup(
            parsedGroupId,
          ).catch(() => {
            navigate('/groups')
          })
          return
        }

        void refreshGroupState()
      },
      [
        currentUser?.id,
        navigate,
        parsedGroupId,
        refreshGroupState,
      ],
    )

  const handleInvitationChange =
    useCallback(
      ({
        type,
        payload,
      }: {
        type: string
        payload:
          GroupInvitationEventPayload
      }) => {
        if (
          payload.group_id !==
          parsedGroupId
        ) {
          return
        }

        setInvitedUserIds(
          (current) => {
            const next =
              new Set(current)

            if (
              type ===
              'group_invitation.created'
            ) {
              next.add(
                payload.recipient_id,
              )
            } else {
              next.delete(
                payload.recipient_id,
              )
            }

            return next
          },
        )
      },
      [parsedGroupId],
    )

  const handleRenamed =
    useCallback(
      ({
        payload,
      }: {
        payload:
          GroupRenamedPayload
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
        setRenameText(
          payload.name,
        )
      },
      [parsedGroupId],
    )

  const handleDeleted =
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

  useRealtimeEvent<GroupInvitationEventPayload>(
    'group_invitation.created',
    handleInvitationChange,
  )
  useRealtimeEvent<GroupInvitationEventPayload>(
    'group_invitation.accepted',
    handleInvitationChange,
  )
  useRealtimeEvent<GroupInvitationEventPayload>(
    'group_invitation.rejected',
    handleInvitationChange,
  )

  useRealtimeEvent(
    'group.member_added',
    handleMemberChange,
  )
  useRealtimeEvent(
    'group.member_removed',
    handleMemberChange,
  )
  useRealtimeEvent(
    'group.member_left',
    handleMemberChange,
  )
  useRealtimeEvent(
    'group.renamed',
    handleRenamed,
  )
  useRealtimeEvent(
    'group.deleted',
    handleDeleted,
  )

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

        const currentMembership =
          memberResult.find(
            (membership) =>
              membership.user.id ===
              userResult.id,
          )

        const isCurrentUserOwner =
          currentMembership?.role ===
          'OWNER'

        const [
          pendingInvitationResult,
          activeInvitationLinkResult,
        ] = isCurrentUserOwner
          ? await Promise.all([
              getGroupPendingInvitations(
                parsedGroupId,
              ),
              getActiveGroupInvitationLinks(
                parsedGroupId,
              ),
            ])
          : [[], []]

        if (cancelled) {
          return
        }

        setGroup(groupResult)
        setMembers(memberResult)
        setFriends(friendResult)
        setCurrentUser(userResult)
        setInvitedUserIds(
          new Set(
            pendingInvitationResult.map(
              (invitation) =>
                invitation.recipient.id,
            ),
          ),
        )
        setActiveInvitationLinks(
          activeInvitationLinkResult,
        )
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
    setBusy('disband')
    setError(null)

    try {
      await disbandGroup(
        parsedGroupId,
      )
      setShowDisbandConfirm(false)
      navigate('/groups')
    } catch (requestError) {
      setError(errorText(requestError))
      setShowDisbandConfirm(false)
    } finally {
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
      setActiveInvitationLinks(
        await getActiveGroupInvitationLinks(
          parsedGroupId,
        ),
      )
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  async function handleRevokeLink(
    linkId: number,
  ) {
    setBusy(`revoke-link-${linkId}`)
    setError(null)

    try {
      await revokeGroupInvitationLink(
        parsedGroupId,
        linkId,
      )

      setActiveInvitationLinks(
        (current) =>
          current.filter(
            (activeLink) =>
              activeLink.id !== linkId,
          ),
      )

      if (link?.id === linkId) {
        setLink(null)
      }

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
        </div>

        <div className="d-flex gap-2">
          <Link
            className="btn btn-primary"
            to={`/groups/${group.id}/messages`}
          >
            <span>Open chat</span>
            {getGroupUnread(
              group.id,
            ) > 0 && (
              <span className="badge rounded-pill text-bg-light text-primary ms-2">
                {getGroupUnread(
                  group.id,
                ) > 99
                  ? '99+'
                  : getGroupUnread(
                      group.id,
                    )}
              </span>
            )}
          </Link>

          {isOwner ? (
            <button
              className="btn btn-outline-danger"
              type="button"
              disabled={busy !== null}
              onClick={() => {
                setError(null)
                setShowDisbandConfirm(true)
              }}
            >
              Delete group
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
                onKeyDown={submitOnEnter}
              />
              <button
                className="btn btn-primary"
                type="submit"
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
                          {membership.role === 'OWNER'
                            ? 'Owner'
                            : 'Member'}
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

                  <p className="text-secondary small">
                    A newly created link is shown only
                    once. Existing link URLs cannot be
                    recovered after a reload, but you can
                    still revoke active links below.
                  </p>

                  <button
                    className="btn btn-outline-primary mb-3"
                    disabled={busy !== null}
                    onClick={() =>
                      void handleCreateLink()
                    }
                  >
                    Create new link
                  </button>

                  {link && (
                    <div className="border rounded p-3 mb-3">
                      <div className="fw-semibold mb-2">
                        Newly created link
                      </div>

                      <input
                        className="form-control mb-2"
                        readOnly
                        value={joinUrl ?? ''}
                      />

                      <div className="small text-secondary">
                        Expires:{' '}
                        {new Date(
                          link.expires_at,
                        ).toLocaleString()}
                      </div>
                    </div>
                  )}

                  <div className="fw-semibold mb-2">
                    Active links
                  </div>

                  {activeInvitationLinks.length === 0 ? (
                    <div className="text-secondary small">
                      No active invitation links.
                    </div>
                  ) : (
                    <div className="vstack gap-2">
                      {activeInvitationLinks.map(
                        (activeLink) => (
                          <div
                            className="border rounded p-3"
                            key={activeLink.id}
                          >
                            <div className="small">
                              Created:{' '}
                              {new Date(
                                activeLink.created_at,
                              ).toLocaleString()}
                            </div>

                            <div className="small text-secondary mb-2">
                              Expires:{' '}
                              {new Date(
                                activeLink.expires_at,
                              ).toLocaleString()}
                            </div>

                            <button
                              className="btn btn-outline-danger btn-sm"
                              disabled={busy !== null}
                              onClick={() =>
                                void handleRevokeLink(
                                  activeLink.id,
                                )
                              }
                            >
                              {busy ===
                              `revoke-link-${activeLink.id}`
                                ? 'Revoking...'
                                : 'Revoke'}
                            </button>
                          </div>
                        ),
                      )}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      {showDisbandConfirm && (
        <>
          <div
            className="modal fade show d-block"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-group-title"
          >
            <div className="modal-dialog modal-dialog-centered">
              <div className="modal-content border-0 shadow-lg">
                <div className="modal-header">
                  <h2
                    className="modal-title fs-5"
                    id="delete-group-title"
                  >
                    Delete this group?
                  </h2>

                  <button
                    className="btn-close"
                    type="button"
                    aria-label="Close"
                    disabled={busy === 'disband'}
                    onClick={() =>
                      setShowDisbandConfirm(false)
                    }
                  />
                </div>

                <div className="modal-body">
                  <p className="mb-2">
                    Are you sure you want to delete{' '}
                    <strong>{group.name}</strong>?
                  </p>
                  <p className="text-secondary mb-0">
                    The group will be removed for everyone.
                    This action cannot be undone.
                  </p>
                </div>

                <div className="modal-footer">
                  <button
                    className="btn btn-outline-secondary"
                    type="button"
                    disabled={busy === 'disband'}
                    onClick={() =>
                      setShowDisbandConfirm(false)
                    }
                  >
                    Cancel
                  </button>

                  <button
                    className="btn btn-danger"
                    type="button"
                    disabled={busy === 'disband'}
                    onClick={() =>
                      void handleDisband()
                    }
                  >
                    {busy === 'disband'
                      ? 'Deleting…'
                      : 'Delete group'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div
            className="modal-backdrop fade show"
            aria-hidden="true"
          />
        </>
      )}
    </section>
  )
}

export default GroupDetailPage
