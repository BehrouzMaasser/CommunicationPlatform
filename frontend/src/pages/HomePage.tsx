import { Link } from 'react-router-dom'

function HomePage() {
  return (
    <>
      <section className="mb-5">
        <p className="text-uppercase text-secondary fw-semibold small mb-2">
          Frontend foundation
        </p>
        <h1 className="display-5 fw-semibold mb-3">
          CommunicationPlatform
        </h1>
        <p className="lead text-secondary col-lg-8 mb-0">
          The React client is running. Next we will connect this interface
          to the Django session and REST API.
        </p>
      </section>

      <section className="row g-3">
        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h2 className="h5 card-title">Friends</h2>
              <p className="card-text text-secondary">
                Friend lists and requests will be our first real React feature.
              </p>
              <Link className="btn btn-outline-primary" to="/friends">
                Open Friends
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h2 className="h5 card-title">Messages</h2>
              <p className="card-text text-secondary">
                Direct conversations, replies, and attachments will live here.
              </p>
              <Link className="btn btn-outline-primary" to="/messages">
                Open Messages
              </Link>
            </div>
          </div>
        </div>

        <div className="col-md-4">
          <div className="card h-100 shadow-sm">
            <div className="card-body">
              <h2 className="h5 card-title">Groups</h2>
              <p className="card-text text-secondary">
                Groups, memberships, and invitations will be connected later.
              </p>
              <Link className="btn btn-outline-primary" to="/groups">
                Open Groups
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  )
}

export default HomePage
