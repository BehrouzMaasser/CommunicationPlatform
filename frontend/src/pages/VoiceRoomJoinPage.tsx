import {
  useState,
} from 'react'
import {
  Link,
  useNavigate,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import {
  joinVoiceRoomWithToken,
} from '../api/voice'


function VoiceRoomJoinPage() {
  const { token } =
    useParams<{ token: string }>()

  const navigate = useNavigate()

  const [joining, setJoining] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)


  async function handleJoin() {
    if (!token) {
      setError(
        'Invitation token is missing.',
      )
      return
    }

    setJoining(true)
    setError(null)

    try {
      await joinVoiceRoomWithToken(
        token,
      )

      navigate('/voice')
    } catch (requestError) {
      if (
        requestError instanceof ApiError
        && requestError.status === 401
      ) {
        const nextUrl =
          encodeURIComponent(
            window.location.href,
          )

        window.location.assign(
          `/accounts/login/?next=${nextUrl}`,
        )
        return
      }

      setError(
        requestError instanceof ApiError
          ? requestError.message
          : requestError instanceof Error
            ? requestError.message
            : 'Could not join Voice Room.',
      )

      setJoining(false)
    }
  }


  return (
    <section
      className="mx-auto"
      style={{ maxWidth: '520px' }}
    >
      <div className="card shadow-sm">
        <div className="card-body text-center py-5">
          <h1 className="h3">
            Voice Room invitation
          </h1>

          <p className="text-secondary">
            Join the Voice Room using this invitation link.
          </p>

          {error && (
            <div className="alert alert-danger text-start">
              {error}
            </div>
          )}

          <div className="d-flex justify-content-center gap-2">
            <Link
              className="btn btn-outline-secondary"
              to="/voice"
            >
              Cancel
            </Link>

            <button
              className="btn btn-primary"
              type="button"
              disabled={joining}
              onClick={() =>
                void handleJoin()
              }
            >
              {joining
                ? 'Joining…'
                : 'Join Voice Room'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}


export default VoiceRoomJoinPage
