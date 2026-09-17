import {
  type FormEvent,
  useRef,
  useState,
} from 'react'
import {
  Link,
} from 'react-router-dom'

import {
  removeCurrentUserAvatar,
  updateCurrentUserAvatar,
} from '../api/users'
import Avatar from '../components/users/Avatar'
import {
  useSession,
} from '../session/useSession'


function AccountPage() {
  const {
    authStatus,
    currentUser,
    updateCurrentUser,
  } = useSession()

  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null,
    )

  const [
    selectedAvatar,
    setSelectedAvatar,
  ] = useState<File | null>(null)

  const [
    avatarError,
    setAvatarError,
  ] = useState<string | null>(null)

  const [
    isSavingAvatar,
    setIsSavingAvatar,
  ] = useState(false)

  async function handleAvatarUpload(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (
      !selectedAvatar
      || isSavingAvatar
    ) {
      return
    }

    setIsSavingAvatar(true)
    setAvatarError(null)

    try {
      const user =
        await updateCurrentUserAvatar(
          selectedAvatar,
        )
      updateCurrentUser(user)

      setSelectedAvatar(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error) {
      setAvatarError(
        error instanceof Error
          ? error.message
          : 'Could not update avatar.',
      )
    } finally {
      setIsSavingAvatar(false)
    }
  }

  async function handleAvatarRemove() {
    if (isSavingAvatar) {
      return
    }

    setIsSavingAvatar(true)
    setAvatarError(null)

    try {
      const user =
        await removeCurrentUserAvatar()
      updateCurrentUser(user)

      setSelectedAvatar(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error) {
      setAvatarError(
        error instanceof Error
          ? error.message
          : 'Could not remove avatar.',
      )
    } finally {
      setIsSavingAvatar(false)
    }
  }

  if (authStatus === 'loading') {
    return (
      <section>
        <h1 className="h3 mb-3">My account</h1>
        <p className="text-secondary mb-0">
          Loading account…
        </p>
      </section>
    )
  }

  if (
    authStatus !== 'authenticated'
    || currentUser === null
  ) {
    return (
      <section>
        <h1 className="h3 mb-3">My account</h1>

        {authStatus === 'error' ? (
          <div className="alert alert-danger mb-0">
            Account information is currently unavailable.
          </div>
        ) : (
          <div className="alert alert-info mb-0">
            <p className="mb-3">
              Sign in to view your account information.
            </p>
            <a
              className="btn btn-primary"
              href="/accounts/login/?next=/account"
            >
              Sign in
            </a>
          </div>
        )}
      </section>
    )
  }

  return (
    <section>
      <div className="mb-4">
        <h1 className="h3 mb-2">My account</h1>
        <p className="text-secondary mb-0">
          Your Communication Platform account information.
        </p>
      </div>

      <div className="row g-4">
        <div className="col-12 col-lg-8">
          <div className="card shadow-sm">
            <div className="card-body p-4">
              <h2 className="h5 mb-3">
                Account details
              </h2>

              <div className="row g-3">
                <div className="col-12">
                  <div className="border rounded-3 p-3">
                    <div className="text-secondary small mb-1">
                      Username
                    </div>
                    <div className="fw-semibold">
                      {currentUser.username}
                    </div>
                  </div>
                </div>

                <div className="col-12">
                  <div className="border rounded-3 p-3">
                    <div className="text-secondary small mb-1">
                      Email
                    </div>
                    <div className="fw-semibold text-break">
                      {currentUser.email}
                    </div>
                  </div>
                </div>
              </div>

              <div className="border-top mt-4 pt-4">
                <Link
                  className="btn btn-outline-primary"
                  to="/"
                >
                  Back to app
                </Link>
              </div>
            </div>
          </div>
        </div>

        <div className="col-12 col-lg-4">
          <div className="card shadow-sm">
            <div className="card-body p-4">
              <h2 className="h5 mb-3">
                Avatar
              </h2>

              <div className="d-flex align-items-center gap-3 mb-4">
                <Avatar
                  user={currentUser}
                  size="xl"
                />
                <div className="small text-secondary">
                  JPEG, PNG or WebP. Images are cropped to a square.
                </div>
              </div>

              <form
                onSubmit={(event) => {
                  void handleAvatarUpload(event)
                }}
              >
                <label
                  className="form-label"
                  htmlFor="account-avatar"
                >
                  Choose image
                </label>
                <input
                  ref={fileInputRef}
                  id="account-avatar"
                  className="form-control"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  disabled={isSavingAvatar}
                  onChange={(event) => {
                    setAvatarError(null)
                    setSelectedAvatar(
                      event.target.files?.[0]
                      ?? null,
                    )
                  }}
                />

                {avatarError && (
                  <div
                    className="alert alert-danger py-2 mt-3 mb-0"
                    role="alert"
                  >
                    {avatarError}
                  </div>
                )}

                <div className="d-flex flex-wrap gap-2 mt-3">
                  <button
                    className="btn btn-primary"
                    type="submit"
                    disabled={
                      !selectedAvatar
                      || isSavingAvatar
                    }
                  >
                    {isSavingAvatar
                      ? 'Saving…'
                      : 'Upload avatar'}
                  </button>

                  {currentUser.avatar_url && (
                    <button
                      className="btn btn-outline-danger"
                      type="button"
                      disabled={isSavingAvatar}
                      onClick={() => {
                        void handleAvatarRemove()
                      }}
                    >
                      Remove
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}


export default AccountPage
