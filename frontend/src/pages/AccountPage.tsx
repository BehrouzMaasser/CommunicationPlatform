import {
  Link,
} from 'react-router-dom'

import {
  useSession,
} from '../session/useSession'


function AccountPage() {
  const {
    authStatus,
    currentUser,
  } = useSession()

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

      <div className="row">
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
      </div>
    </section>
  )
}


export default AccountPage
