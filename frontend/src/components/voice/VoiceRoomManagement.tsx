import {
  type SyntheticEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { ApiError } from '../../api/client'
import {
  getFriends,
} from '../../api/friendships'
import {
  cancelVoiceRoomInvitation,
  createVoiceRoomInvitationLink,
  getVoiceRoomInvitationLinks,
  getVoiceRoomPendingInvitations,
  inviteUserToVoiceRoom,
  revokeVoiceRoomInvitationLink,
} from '../../api/voice'
import {
  useRealtimeEvent,
} from '../../realtime/useRealtime'
import Avatar from '../users/Avatar'

import type {
  VoiceRoom,
  VoiceRoomInvitation,
  VoiceRoomInvitationLink,
  VoiceRoomMembership,
} from '../../types/voice'
import type {
  PublicUser,
} from '../../types/users'


type Props = {
  room: VoiceRoom
  members: VoiceRoomMembership[]
}


type RoomEventPayload = {
  room_id: string
}


function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}


function invitationUrl(
  token: string,
): string {
  return (
    `${window.location.origin}/voice/join/`
    + encodeURIComponent(token)
  )
}


function selectInputText(
  event: SyntheticEvent<HTMLInputElement>,
) {
  event.currentTarget.select()
}


function VoiceRoomManagement({
  room,
  members,
}: Props) {
  const [friends, setFriends] =
    useState<PublicUser[]>([])

  const [
    pendingInvitations,
    setPendingInvitations,
  ] =
    useState<VoiceRoomInvitation[]>([])

  const [links, setLinks] =
    useState<VoiceRoomInvitationLink[]>([])

  const [loading, setLoading] =
    useState(true)

  const [busy, setBusy] =
    useState<string | null>(null)

  const [error, setError] =
    useState<string | null>(null)

  const [notice, setNotice] =
    useState<string | null>(null)

  const [copiedLinkId, setCopiedLinkId] =
    useState<string | null>(null)


  const refresh =
    useCallback(
      async () => {
        const [
          friendResult,
          invitationResult,
          linkResult,
        ] = await Promise.all([
          getFriends(),
          getVoiceRoomPendingInvitations(
            room.id,
          ),
          getVoiceRoomInvitationLinks(
            room.id,
          ),
        ])

        setFriends(friendResult)
        setPendingInvitations(
          invitationResult,
        )
        setLinks(linkResult)
      },
      [room.id],
    )


  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [
          friendResult,
          invitationResult,
          linkResult,
        ] = await Promise.all([
          getFriends(),
          getVoiceRoomPendingInvitations(
            room.id,
          ),
          getVoiceRoomInvitationLinks(
            room.id,
          ),
        ])

        if (!cancelled) {
          setFriends(friendResult)
          setPendingInvitations(
            invitationResult,
          )
          setLinks(linkResult)
        }
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
  }, [room.id])


  const handleRoomEvent =
    useCallback(
      ({
        payload,
      }: {
        payload: RoomEventPayload
      }) => {
        if (
          payload.room_id === room.id
        ) {
          void refresh()
        }
      },
      [
        refresh,
        room.id,
      ],
    )


  useRealtimeEvent<RoomEventPayload>(
    'voice_room_invitation.created',
    handleRoomEvent,
  )

  useRealtimeEvent<RoomEventPayload>(
    'voice_room_invitation.accepted',
    handleRoomEvent,
  )

  useRealtimeEvent<RoomEventPayload>(
    'voice_room_invitation.rejected',
    handleRoomEvent,
  )

  useRealtimeEvent<RoomEventPayload>(
    'voice_room_invitation.cancelled',
    handleRoomEvent,
  )

  useRealtimeEvent<RoomEventPayload>(
    'voice_room.member_added',
    handleRoomEvent,
  )

  useRealtimeEvent<RoomEventPayload>(
    'voice_room.invite_link_created',
    handleRoomEvent,
  )

  useRealtimeEvent<RoomEventPayload>(
    'voice_room.invite_link_revoked',
    handleRoomEvent,
  )


  const memberIds =
    useMemo(
      () =>
        new Set(
          members.map(
            (membership) =>
              membership.user.id,
          ),
        ),
      [members],
    )


  const pendingByUserId =
    useMemo(
      () =>
        new Map(
          pendingInvitations.map(
            (invitation) => [
              invitation.recipient.id,
              invitation,
            ],
          ),
        ),
      [pendingInvitations],
    )


  const inviteCandidates =
    friends.filter(
      (friend) =>
        !memberIds.has(friend.id),
    )


  async function handleInvite(
    friend: PublicUser,
  ) {
    const key =
      `invite-${friend.id}`

    setBusy(key)
    setError(null)
    setNotice(null)

    try {
      const invitation =
        await inviteUserToVoiceRoom(
          room.id,
          friend.id,
        )

      setPendingInvitations(
        (current) => [
          ...current.filter(
            (item) =>
              item.id !== invitation.id,
          ),
          invitation,
        ],
      )

      setNotice(
        `Invitation sent to @${friend.username}.`,
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setBusy(null)
    }
  }


  async function handleCancel(
    invitation: VoiceRoomInvitation,
  ) {
    const key =
      `cancel-${invitation.id}`

    setBusy(key)
    setError(null)
    setNotice(null)

    try {
      await cancelVoiceRoomInvitation(
        room.id,
        invitation.id,
      )

      setPendingInvitations(
        (current) =>
          current.filter(
            (item) =>
              item.id !== invitation.id,
          ),
      )

      setNotice(
        `Invitation to @${invitation.recipient.username} cancelled.`,
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setBusy(null)
    }
  }


  async function handleCreateLink() {
    setBusy('create-link')
    setError(null)
    setNotice(null)

    try {
      const link =
        await createVoiceRoomInvitationLink(
          room.id,
        )

      setLinks(
        (current) => [
          link,
          ...current.filter(
            (item) =>
              item.id !== link.id,
          ),
        ],
      )

      setNotice(
        'Invitation link created.',
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setBusy(null)
    }
  }


  async function handleCopyLink(
    link: VoiceRoomInvitationLink,
  ) {
    if (!link.token) {
      setError(
        'This invitation link cannot be recovered.',
      )
      return
    }

    setError(null)

    try {
      await navigator.clipboard.writeText(
        invitationUrl(link.token),
      )

      setCopiedLinkId(link.id)
      setNotice(
        'Invitation link copied.',
      )
    } catch {
      setError(
        'Could not copy the invitation link automatically. Select it and copy it manually.',
      )
    }
  }


  async function handleRevokeLink(
    link: VoiceRoomInvitationLink,
  ) {
    const key =
      `revoke-${link.id}`

    setBusy(key)
    setError(null)
    setNotice(null)

    try {
      await revokeVoiceRoomInvitationLink(
        room.id,
        link.id,
      )

      setLinks(
        (current) =>
          current.filter(
            (item) =>
              item.id !== link.id,
          ),
      )

      setNotice(
        'Invitation link revoked.',
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setBusy(null)
    }
  }


  if (loading) {
    return (
      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <div
            className="spinner-border spinner-border-sm"
            role="status"
          />
        </div>
      </div>
    )
  }


  return (
    <>
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

      <div className="row g-4 mb-4">
        <div className="col-lg-6">
          <div className="card shadow-sm h-100">
            <div className="card-body">
              <h2 className="h5 mb-3">
                Invite friends
              </h2>

              {inviteCandidates.length === 0 ? (
                <p className="text-secondary mb-0">
                  No current friends available to invite.
                </p>
              ) : (
                <div className="list-group list-group-flush">
                  {inviteCandidates.map(
                    (friend) => {
                      const invitation =
                        pendingByUserId.get(
                          friend.id,
                        )

                      return (
                        <div
                          className="list-group-item px-0 d-flex justify-content-between align-items-center gap-3"
                          key={friend.id}
                        >
                          <div className="directory-user-identity">
                            <Avatar
                              user={friend}
                              size="sm"
                              alt=""
                            />
                            <span className="directory-user-name">
                              @{friend.username}
                            </span>
                          </div>

                          {invitation ? (
                            <button
                              className="btn btn-sm btn-outline-secondary"
                              type="button"
                              disabled={
                                busy !== null
                              }
                              onClick={() =>
                                void handleCancel(
                                  invitation,
                                )
                              }
                            >
                              {busy ===
                              `cancel-${invitation.id}`
                                ? 'Cancelling…'
                                : 'Cancel invitation'}
                            </button>
                          ) : (
                            <button
                              className="btn btn-sm btn-primary"
                              type="button"
                              disabled={
                                busy !== null
                              }
                              onClick={() =>
                                void handleInvite(
                                  friend,
                                )
                              }
                            >
                              {busy ===
                              `invite-${friend.id}`
                                ? 'Inviting…'
                                : 'Invite'}
                            </button>
                          )}
                        </div>
                      )
                    },
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="col-lg-6">
          <div className="card shadow-sm h-100">
            <div className="card-body">
              <div className="d-flex justify-content-between align-items-center gap-3 mb-3">
                <h2 className="h5 mb-0">
                  Invitation links
                </h2>

                <button
                  className="btn btn-sm btn-outline-primary"
                  type="button"
                  disabled={busy !== null}
                  onClick={() =>
                    void handleCreateLink()
                  }
                >
                  {busy === 'create-link'
                    ? 'Creating…'
                    : 'Create link'}
                </button>
              </div>

              {links.length === 0 ? (
                <p className="text-secondary mb-0">
                  No active invitation links.
                </p>
              ) : (
                <div className="vstack gap-3">
                  {links.map((link) => (
                    <div
                      className="border rounded p-3"
                      key={link.id}
                    >
                      {link.token ? (
                        <div className="input-group input-group-sm mb-2">
                          <input
                            className="form-control"
                            readOnly
                            value={
                              invitationUrl(
                                link.token,
                              )
                            }
                            onClick={
                              selectInputText
                            }
                            onFocus={
                              selectInputText
                            }
                            aria-label="Voice room invitation link"
                          />

                          <button
                            className="btn btn-outline-secondary"
                            type="button"
                            disabled={
                              busy !== null
                            }
                            onClick={() =>
                              void handleCopyLink(
                                link,
                              )
                            }
                          >
                            {copiedLinkId ===
                            link.id
                              ? 'Copied!'
                              : 'Copy'}
                          </button>
                        </div>
                      ) : (
                        <div className="small text-secondary mb-2">
                          This link cannot be copied again.
                        </div>
                      )}

                      <div className="small text-secondary mb-2">
                        Expires:{' '}
                        {new Date(
                          link.expires_at,
                        ).toLocaleString()}
                      </div>

                      <button
                        className="btn btn-sm btn-outline-danger"
                        type="button"
                        disabled={busy !== null}
                        onClick={() =>
                          void handleRevokeLink(
                            link,
                          )
                        }
                      >
                        {busy ===
                        `revoke-${link.id}`
                          ? 'Revoking…'
                          : 'Revoke'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}


export default VoiceRoomManagement
