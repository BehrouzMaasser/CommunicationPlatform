import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Link,
} from 'react-router-dom'

import { ApiError } from '../api/client'
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
    <section>
      <div className="mb-4">
        <h1 className="h2 mb-1">
          Voice Rooms
        </h1>

        <p className="text-secondary mb-0">
          Persistent voice rooms you can join whenever you want.
        </p>
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

      {invitations.length > 0 && (
        <div className="card shadow-sm mb-4">
          <div className="card-body">
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h2 className="h5 mb-0">
                Invitations
              </h2>

              <span className="badge text-bg-primary">
                {invitations.length}
              </span>
            </div>

            <div className="list-group list-group-flush">
              {invitations.map(
                (invitation) => (
                  <div
                    className="list-group-item px-0 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3"
                    key={invitation.id}
                  >
                    <div>
                      <div className="fw-semibold">
                        {invitation.room_name}
                      </div>

                      <div className="small text-secondary">
                        Invited by @{invitation.invited_by.username}
                      </div>
                    </div>

                    <div className="d-flex gap-2">
                      <button
                        className="btn btn-sm btn-primary"
                        type="button"
                        disabled={
                          busy !== null
                        }
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
                        disabled={
                          busy !== null
                        }
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
          </div>
        </div>
      )}

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h5 mb-3">
            Create a Voice Room
          </h2>

          <form
            className="d-flex flex-column flex-sm-row gap-2"
            onSubmit={handleCreate}
          >
            <input
              className="form-control"
              maxLength={50}
              value={name}
              onChange={(event) =>
                setName(
                  event.target.value,
                )
              }
              placeholder="Room name"
              aria-label="Voice room name"
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
                : 'Create'}
            </button>
          </form>
        </div>
      </div>

      <div className="card shadow-sm">
        <div className="card-body">
          <div className="d-flex justify-content-between align-items-center mb-3">
            <h2 className="h5 mb-0">
              Your Voice Rooms
            </h2>

            <span className="badge text-bg-secondary">
              {rooms.length}
            </span>
          </div>

          {rooms.length === 0 ? (
            <p className="text-secondary mb-0">
              You are not a member of any Voice Rooms yet.
            </p>
          ) : (
            <div className="list-group">
              {rooms.map((room) => (
                <Link
                  className="list-group-item list-group-item-action"
                  key={room.id}
                  to={`/voice/rooms/${room.id}`}
                >
                  <div className="d-flex justify-content-between align-items-center gap-3">
                    <div>
                      <div className="fw-semibold">
                        {room.name}
                      </div>

                      <div className="small text-secondary">
                        Owner @{room.owner.username}
                      </div>
                    </div>

                    <div className="d-flex flex-wrap justify-content-end gap-2">
                      {room.connected_count > 0 && (
                        <span className="badge text-bg-success">
                          {room.connected_count}{' '}
                          connected
                        </span>
                      )}

                      <span className="badge text-bg-secondary">
                        {room.member_count}{' '}
                        {room.member_count === 1
                          ? 'member'
                          : 'members'}
                      </span>
                    </div>
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


export default VoiceRoomsPage
