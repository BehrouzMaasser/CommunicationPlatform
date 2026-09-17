import {
  type FormEvent,
  useRef,
  useState,
} from 'react'

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
    avatarNotice,
    setAvatarNotice,
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
    setAvatarNotice(null)

    try {
      const user =
        await updateCurrentUserAvatar(
          selectedAvatar,
        )
      updateCurrentUser(user)

      setSelectedAvatar(null)
      setAvatarNotice(
        'Avatar updated.',
      )
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
    setAvatarNotice(null)

    try {
      const user =
        await removeCurrentUserAvatar()
      updateCurrentUser(user)

      setSelectedAvatar(null)
      setAvatarNotice(
        'Avatar removed.',
      )
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
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading account"
        />
      </div>
    )
  }

  if (
    authStatus !== 'authenticated'
    || currentUser === null
  ) {
    return (
      <section className="account-page">
        <div className="directory-page-header">
          <div>
            <h1 className="directory-page-title mb-1">
              Account
            </h1>
            <p className="directory-page-subtitle mb-0">
              Your account information.
            </p>
          </div>
        </div>

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
    <section className="account-page">
      <div className="directory-page-header account-page-header">
        <div className="account-page-identity">
          <Avatar
            user={currentUser}
            size="xl"
          />

          <div className="min-width-0">
            <h1 className="directory-page-title mb-1 text-truncate">
              {currentUser.username}
            </h1>
            <p className="directory-page-subtitle mb-0 text-truncate">
              {currentUser.email}
            </p>
          </div>
        </div>
      </div>

      <div className="account-page-grid">
        <section className="directory-surface">
          <div className="directory-section-header">
            <div>
              <h2 className="directory-section-title">
                Account details
              </h2>
              <p className="directory-section-subtitle mb-0">
                Basic information associated with your account.
              </p>
            </div>
          </div>

          <dl className="account-detail-list mb-0">
            <div className="account-detail-row">
              <dt>Username</dt>
              <dd>@{currentUser.username}</dd>
            </div>
            <div className="account-detail-row">
              <dt>Email</dt>
              <dd>{currentUser.email}</dd>
            </div>
          </dl>
        </section>

        <section className="directory-surface">
          <div className="directory-section-header">
            <div>
              <h2 className="directory-section-title">
                Avatar
              </h2>
              <p className="directory-section-subtitle mb-0">
                JPEG, PNG or WebP. Images are cropped to a square.
              </p>
            </div>
          </div>

          <form
            className="account-avatar-form"
            onSubmit={(event) => {
              void handleAvatarUpload(event)
            }}
          >
            <input
              ref={fileInputRef}
              id="account-avatar"
              className="form-control"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              disabled={isSavingAvatar}
              aria-label="Choose avatar image"
              onChange={(event) => {
                setAvatarError(null)
                setAvatarNotice(null)
                setSelectedAvatar(
                  event.target.files?.[0]
                  ?? null,
                )
              }}
            />

            {selectedAvatar && (
              <div className="account-selected-file">
                Selected: {selectedAvatar.name}
              </div>
            )}

            {avatarError && (
              <div
                className="alert alert-danger py-2 mb-0"
                role="alert"
              >
                {avatarError}
              </div>
            )}

            {avatarNotice && (
              <div
                className="alert alert-success py-2 mb-0"
                role="status"
              >
                {avatarNotice}
              </div>
            )}

            <div className="d-flex flex-wrap gap-2">
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
                  Remove avatar
                </button>
              )}
            </div>
          </form>
        </section>
      </div>
    </section>
  )
}


export default AccountPage
