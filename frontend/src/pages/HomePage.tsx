import { Link } from 'react-router-dom'

function HomePage() {
  return (
    <div className="home-page">
      <section className="hero-panel overflow-hidden">
        <div className="row align-items-center g-5">
          <div className="col-lg-7">
            <div className="hero-kicker mb-3">
              <span className="hero-kicker-dot" aria-hidden="true" />
              Your conversations, in one place
            </div>

            <h1 className="hero-title mb-4">
              Stay close to the people who matter.
            </h1>

            <p className="hero-copy mb-4">
              Chat privately, keep up with friends, and bring everyone together
              in groups — with updates that arrive in real time.
            </p>

            <div className="d-flex flex-wrap gap-2 gap-sm-3">
              <Link className="btn btn-primary btn-lg px-4" to="/messages">
                Open messages
              </Link>

              <Link className="btn btn-soft btn-lg px-4" to="/friends">
                Find friends
              </Link>
            </div>
          </div>

          <div className="col-lg-5 d-none d-lg-block" aria-hidden="true">
            <div className="hero-visual">
              <div className="hero-orb hero-orb-one" />
              <div className="hero-orb hero-orb-two" />

              <div className="mock-chat-card mock-chat-card-back">
                <div className="mock-avatar">M</div>
                <div className="flex-grow-1">
                  <div className="mock-line mock-line-title" />
                  <div className="mock-line mock-line-short" />
                </div>
              </div>

              <div className="mock-chat-card mock-chat-card-front">
                <div className="d-flex align-items-center gap-3 mb-4">
                  <div className="mock-avatar mock-avatar-accent">A</div>
                  <div className="flex-grow-1">
                    <div className="mock-line mock-line-title" />
                    <div className="mock-line mock-line-short" />
                  </div>
                  <span className="mock-online-dot" />
                </div>

                <div className="mock-message mock-message-incoming" />
                <div className="mock-message mock-message-outgoing" />
                <div className="mock-message mock-message-incoming mock-message-small" />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="d-flex flex-column flex-md-row align-items-md-end justify-content-between gap-2 mb-4">
          <div>
            <p className="section-eyebrow mb-2">Everything you need</p>
            <h2 className="h2 fw-bold mb-0">Pick up where you left off</h2>
          </div>
          <p className="text-secondary mb-0 home-section-copy">
            Friends, direct chats, and groups stay just one click away.
          </p>
        </div>

        <div className="row g-3 g-lg-4">
          <div className="col-md-4">
            <Link className="feature-card h-100" to="/friends">
              <span className="feature-icon feature-icon-friends" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M16 11a4 4 0 1 0-3.95-4.62A5 5 0 1 0 8 14c-3.31 0-6 1.79-6 4v1h10v-1c0-1.05.38-2.02 1.04-2.86A7.7 7.7 0 0 1 16 14c3.31 0 6 1.79 6 4v1h-8v-1c0-1.42-.72-2.72-1.92-3.74A4 4 0 0 0 16 11Z" />
                </svg>
              </span>
              <span className="feature-card-title">Friends</span>
              <span className="feature-card-copy">
                Find people, manage requests, and keep your connections close.
              </span>
              <span className="feature-card-link">View friends <span aria-hidden="true">→</span></span>
            </Link>
          </div>

          <div className="col-md-4">
            <Link className="feature-card h-100" to="/messages">
              <span className="feature-icon feature-icon-messages" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M4 3h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H9l-5.5 3.5.9-3.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm2 5h12V6H6v2Zm0 4h9v-2H6v2Z" />
                </svg>
              </span>
              <span className="feature-card-title">Messages</span>
              <span className="feature-card-copy">
                Continue direct conversations with replies, files, and live updates.
              </span>
              <span className="feature-card-link">Open messages <span aria-hidden="true">→</span></span>
            </Link>
          </div>

          <div className="col-md-4">
            <Link className="feature-card h-100" to="/groups">
              <span className="feature-icon feature-icon-groups" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M12 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM5.5 6a3.5 3.5 0 0 1 2.24.81A5.95 5.95 0 0 0 8 9.5c0 .37.03.72.1 1.07A3.5 3.5 0 1 1 5.5 6Zm13 0a3.5 3.5 0 1 1-2.6 4.57c.07-.35.1-.7.1-1.07 0-.95-.22-1.86-.62-2.69A3.5 3.5 0 0 1 18.5 6ZM12 12c3.87 0 7 2.24 7 5v3H5v-3c0-2.76 3.13-5 7-5Zm-8.08.18A7.9 7.9 0 0 0 1 14.1V18h2v-1c0-1.7.76-3.24 2.03-4.48a5.5 5.5 0 0 1-1.11-.34Zm16.16 0c-.36.15-.73.27-1.11.34A6.2 6.2 0 0 1 21 17v1h2v-3.9a7.9 7.9 0 0 0-2.92-1.92Z" />
                </svg>
              </span>
              <span className="feature-card-title">Groups</span>
              <span className="feature-card-copy">
                Create shared spaces, invite people, and keep group chats moving.
              </span>
              <span className="feature-card-link">Browse groups <span aria-hidden="true">→</span></span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}

export default HomePage
