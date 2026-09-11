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
  joinGroupWithToken,
} from '../api/groups'

function GroupJoinPage() {
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
      await joinGroupWithToken(token)
      navigate('/groups')
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : requestError instanceof Error
            ? requestError.message
            : 'Could not join group.',
      )
      setJoining(false)
    }
  }

  return (
    <section className="mx-auto" style={{ maxWidth: '520px' }}>
      <div className="card shadow-sm">
        <div className="card-body text-center py-5">
          <h1 className="h3">
            Group invitation
          </h1>

          <p className="text-secondary">
            Join the group using this invitation link.
          </p>

          {error && (
            <div className="alert alert-danger text-start">
              {error}
            </div>
          )}

          <div className="d-flex justify-content-center gap-2">
            <Link
              className="btn btn-outline-secondary"
              to="/groups"
            >
              Cancel
            </Link>

            <button
              className="btn btn-primary"
              disabled={joining}
              onClick={() =>
                void handleJoin()
              }
            >
              {joining
                ? 'Joining…'
                : 'Join group'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

export default GroupJoinPage
