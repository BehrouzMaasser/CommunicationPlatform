import {
  type FormEvent,
  useEffect,
  useState,
} from 'react'
import { Link } from 'react-router-dom'

import { ApiError } from '../api/client'
import {
  createVoiceRoom,
  getVoiceRooms,
} from '../api/voice'

import type {
  VoiceRoom,
} from '../types/voice'


function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}


function VoiceRoomsPage() {
  const [rooms, setRooms] =
    useState<VoiceRoom[]>([])

  const [name, setName] =
    useState('')

  const [loading, setLoading] =
    useState(true)

  const [creating, setCreating] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)


  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data =
          await getVoiceRooms()

        if (!cancelled) {
          setRooms(data)
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

    const trimmedName =
      name.trim()

    if (!trimmedName || creating) {
      return
    }

    setCreating(true)
    setError(null)

    try {
      const room =
        await createVoiceRoom(
          trimmedName,
        )

      setRooms((current) => [
        room,
        ...current.filter(
          (existingRoom) =>
            existingRoom.id !== room.id,
        ),
      ])

      setName('')
    } catch (requestError) {
      setError(
        errorText(requestError),
      )
    } finally {
      setCreating(false)
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
          Persistent rooms for voice conversations.
        </p>
      </div>

      {error && (
        <div
          className="alert alert-danger"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <h2 className="h5">
            Create voice room
          </h2>

          <form
            className="d-flex gap-2"
            onSubmit={handleCreate}
          >
            <input
              className="form-control"
              value={name}
              maxLength={50}
              onChange={(event) =>
                setName(
                  event.target.value,
                )
              }
              placeholder="Room name"
            />

            <button
              className="btn btn-primary text-nowrap"
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
              Your voice rooms
            </h2>

            <span className="badge text-bg-secondary">
              {rooms.length}
            </span>
          </div>

          {rooms.length === 0 ? (
            <p className="text-secondary mb-0">
              You are not in any voice rooms yet.
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

                    <span className="badge text-bg-secondary">
                      {room.member_count}{' '}
                      {room.member_count === 1
                        ? 'member'
                        : 'members'}
                    </span>
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
