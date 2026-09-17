import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'
import {
  Link,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import VoiceRoomAvatar from '../components/voice/VoiceRoomAvatar'
import {
  acceptVoiceRoomInvitation,
  createVoiceRoom,
  getIncomingVoiceRoomInvitations,
  getVoiceRooms,
  rejectVoiceRoomInvitation,
} from '../api/voice'
import {
  useRealtimeEvent,
} from '../realtime/RealtimeContext'

import type {
  VoiceRoom,
  VoiceRoomInvitation,
} from '../types/voice'


function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}


async function loadVoiceRoomsPage() {
  const [
    rooms,
    invitations,
  ] = await Promise.all([
    getVoiceRooms(),
    getIncomingVoiceRoomInvitations(),
  ])

  return {
    rooms,
    invitations,
  }
}


function VoiceRoomsPage() {
  const [rooms, setRooms] =
    useState<VoiceRoom[]>([])

  const [
    invitations,
    setInvitations,
  ] =
    useState<VoiceRoomInvitation[]>([])

  const [name, setName] =
    useState('')

  const [searchQuery, setSearchQuery] =
    useState('')

  const [createOpen, setCreateOpen] =
    useState(false)

  const [loading, setLoading] =
    useState(true)

  const [creating, setCreating] =
    useState(false)

  const [busy, setBusy] =
    useState<string | null>(null)

  const [error, setError] =
    useState<string | null>(null)

  const [notice, setNotice] =
    useState<string | null>(null)


  const refresh =
    useCallback(
      async () => {
        const data =
          await loadVoiceRoomsPage()

        setRooms(data.rooms)
        setInvitations(
          data.invitations,
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


  useRealtimeEvent(
    'voice_room.created',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room.deleted',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room.member_added',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room.member_left',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room.member_removed',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room_invitation.created',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room_invitation.accepted',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room_invitation.rejected',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room_invitation.cancelled',
    handleRealtimeChange,
  )


  useRealtimeEvent(
    'voice.room.participant_joined',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice.room.participant_left',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice.room.participant_revoked',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice.room.session_ended',
    handleRealtimeChange,
  )


  useRealtimeEvent(
    'voice_room.renamed',
    handleRealtimeChange,
  )

  useRealtimeEvent(
    'voice_room.avatar_updated',
    handleRealtimeChange,
  )


  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data =
          await loadVoiceRoomsPage()

        if (!cancelled) {
          setRooms(data.rooms)
          setInvitations(
            data.invitations,
          )
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
  }, [])


  async function handleCreate(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const trimmed = name.trim()

    if (!trimmed || creating) {
      return
    }

    setCreating(true)
    setError(null)
    setNotice(null)

    try {
      const room =
        await createVoiceRoom(
          trimmed,
        )

      setRooms(
        (current) => [
          room,
          ...current.filter(
            (item) =>
              item.id !== room.id,
          ),
        ],
      )

      setName('')
      setCreateOpen(false)
      setNotice(
        `Voice Room "${room.name}" created.`,
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setCreating(false)
    }
  }


  async function handleAccept(
    invitation: VoiceRoomInvitation,
  ) {
    const key =
      `accept-${invitation.id}`

    setBusy(key)
    setError(null)
    setNotice(null)

    try {
      await acceptVoiceRoomInvitation(
        invitation.id,
      )

      await refresh()

      setNotice(
        `Joined "${invitation.room_name}".`,
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setBusy(null)
    }
  }


  async function handleReject(
    invitation: VoiceRoomInvitation,
  ) {
    const key =
      `reject-${invitation.id}`

    setBusy(key)
    setError(null)
    setNotice(null)

    try {
      await rejectVoiceRoomInvitation(
        invitation.id,
      )

      setInvitations(
        (current) =>
          current.filter(
            (item) =>
              item.id !== invitation.id,
          ),
      )

      setNotice(
        `Invitation to "${invitation.room_name}" rejected.`,
      )
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setBusy(null)
    }
  }


  const normalizedQuery =
    searchQuery.trim().toLocaleLowerCase()

  const filteredRooms =
    useMemo(
      () => {
        if (!normalizedQuery) {
          return rooms
        }

        return rooms.filter(
          (room) =>
            room.name
              .toLocaleLowerCase()
              .includes(normalizedQuery)
            || room.owner.username
              .toLocaleLowerCase()
              .includes(normalizedQuery),
        )
      },
      [normalizedQuery, rooms],
    )


  if (loading) {
    return (
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading voice rooms"
        />
      </div>
    )
  }


  return (
    <section className="voice-rooms-page">
      <div className="directory-page-header">
        <div>
          <h1 className="directory-page-title mb-1">
            Voice Rooms
          </h1>
          <p className="directory-page-subtitle mb-0">
            Persistent rooms you can join whenever people are around.
          </p>
        </div>

        <button
          className={`directory-primary-action${createOpen ? ' is-active' : ''}`}
          type="button"
          aria-expanded={createOpen}
          aria-controls="voice-room-create-panel"
          onClick={() => {
            setCreateOpen(
              (current) => !current,
            )
          }}
        >
          <span aria-hidden="true">
            {createOpen ? '×' : '+'}
          </span>
          <span className="directory-primary-action-label">
            {createOpen ? 'Close' : 'New room'}
          </span>
        </button>
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

      {createOpen && (
        <section
          id="voice-room-create-panel"
          className="directory-surface directory-create-panel"
        >
          <div className="directory-section-header">
            <div>
              <h2 className="directory-section-title">
                Create a Voice Room
              </h2>
              <p className="directory-section-subtitle mb-0">
                Give the room a name. You can invite friends after creation.
              </p>
            </div>
          </div>

          <form
            className="directory-create-form"
            onSubmit={handleCreate}
          >
            <input
              className="form-control directory-search-input"
              maxLength={50}
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value,
                )
              }
              placeholder="Room name"
              aria-label="Voice room name"
              autoFocus
            />

            <button
              className="btn btn-primary"
              type="submit"
              disabled={
                creating
                || !name.trim()
              }
            >
              {creating
                ? 'Creating…'
                : 'Create room'}
            </button>
          </form>
        </section>
      )}

      {invitations.length > 0 && (
        <section className="directory-surface voice-room-invitations">
          <div className="directory-section-header">
            <div>
              <h2 className="directory-section-title">
                Invitations
              </h2>
              <p className="directory-section-subtitle mb-0">
                Rooms waiting for your response.
              </p>
            </div>

            <span className="directory-section-count">
              {invitations.length}
            </span>
          </div>

          <div className="directory-list directory-list-compact">
            {invitations.map(
              (invitation) => (
                <div
                  className="directory-request-row"
                  key={invitation.id}
                >
                  <div className="voice-room-list-identity">
                    <VoiceRoomAvatar
                      name={invitation.room_name}
                      avatarUrl={invitation.room_avatar_url}
                      size="sm"
                    />
                    <div className="voice-room-list-copy">
                      <div className="voice-room-list-name">
                        {invitation.room_name}
                      </div>
                      <div className="voice-room-list-meta">
                        Invited by @{invitation.invited_by.username}
                      </div>
                    </div>
                  </div>

                  <div className="directory-request-actions">
                    <button
                      className="btn btn-sm btn-primary"
                      type="button"
                      disabled={busy !== null}
                      onClick={() =>
                        void handleAccept(
                          invitation,
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
                      type="button"
                      disabled={busy !== null}
                      onClick={() =>
                        void handleReject(
                          invitation,
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
              ),
            )}
          </div>
        </section>
      )}

      <section className="directory-surface voice-room-directory">
        <div className="directory-section-header voice-room-directory-header">
          <div>
            <h2 className="directory-section-title">
              Your Voice Rooms
            </h2>
            <p className="directory-section-subtitle mb-0">
              {rooms.length}{' '}
              {rooms.length === 1
                ? 'room'
                : 'rooms'}
            </p>
          </div>

          <label className="voice-room-search">
            <span className="visually-hidden">
              Search Voice Rooms
            </span>
            <input
              className="form-control directory-search-input"
              type="search"
              value={searchQuery}
              placeholder="Search rooms"
              autoComplete="off"
              onChange={(event) => {
                setSearchQuery(
                  event.target.value,
                )
              }}
            />
          </label>
        </div>

        {rooms.length === 0 ? (
          <DirectoryEmpty
            title="No Voice Rooms yet"
            text="Create one or accept an invitation to get started."
          />
        ) : filteredRooms.length === 0 ? (
          <DirectoryEmpty
            title="No matching rooms"
            text="Try a different room or owner name."
          />
        ) : (
          <div className="voice-room-directory-list">
            {filteredRooms.map((room) => (
              <Link
                className="voice-room-directory-row"
                key={room.id}
                to={`/voice/rooms/${room.id}`}
              >
                <VoiceRoomAvatar
                  name={room.name}
                  avatarUrl={room.avatar_url}
                  size="md"
                />

                <span className="voice-room-list-copy">
                  <span className="voice-room-list-row-top">
                    <span className="voice-room-list-name">
                      {room.name}
                    </span>
                    {room.connected_count > 0 && (
                      <span className="voice-room-live-pill">
                        <span className="voice-room-live-dot" aria-hidden="true" />
                        {room.connected_count} live
                      </span>
                    )}
                  </span>

                  <span className="voice-room-list-row-bottom">
                    <span className="voice-room-list-meta">
                      Owner @{room.owner.username}
                    </span>
                    <span className="voice-room-list-meta">
                      {room.member_count}{' '}
                      {room.member_count === 1
                        ? 'member'
                        : 'members'}
                    </span>
                  </span>
                </span>

                <span
                  className="voice-room-row-chevron"
                  aria-hidden="true"
                >
                  ›
                </span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </section>
  )
}

function DirectoryEmpty({
  title,
  text,
}: {
  title: string
  text: string
}) {
  return (
    <div className="directory-empty">
      <div className="fw-semibold">
        {title}
      </div>
      <p className="small text-secondary mb-0">
        {text}
      </p>
    </div>
  )
}


export default VoiceRoomsPage
