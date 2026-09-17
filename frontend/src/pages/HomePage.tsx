import {
  Link,
} from 'react-router-dom'

import {
  useActivity,
} from '../activity/useActivity'
import Avatar from '../components/users/Avatar'
import {
  useSession,
} from '../session/useSession'


type DashboardCardProps = {
  to: string
  label: string
  description: string
  count?: number
  countLabel?: string
  icon: string
}


function DashboardCard({
  to,
  label,
  description,
  count = 0,
  countLabel,
  icon,
}: DashboardCardProps) {
  return (
    <Link
      className="home-dashboard-card"
      to={to}
    >
      <span
        className="home-dashboard-card-icon"
        aria-hidden="true"
      >
        {icon}
      </span>

      <span className="home-dashboard-card-copy">
        <span className="home-dashboard-card-title">
          {label}
        </span>
        <span className="home-dashboard-card-description">
          {description}
        </span>
      </span>

      {count > 0 && (
        <span
          className="home-dashboard-card-count"
          aria-label={
            countLabel
              ? `${count} ${countLabel}`
              : undefined
          }
        >
          {count > 99 ? '99+' : count}
        </span>
      )}

      <span
        className="home-dashboard-card-chevron"
        aria-hidden="true"
      >
        ›
      </span>
    </Link>
  )
}


function HomePage() {
  const {
    currentUser,
  } = useSession()

  const {
    pendingFriendRequests,
    pendingGroupInvitations,
    pendingVoiceRoomInvitations,
    unreadDirectMessages,
    unreadGroupMessages,
  } = useActivity()

  const groupActivity =
    unreadGroupMessages
    + pendingGroupInvitations

  const totalAttention =
    pendingFriendRequests
    + pendingGroupInvitations
    + pendingVoiceRoomInvitations
    + unreadDirectMessages
    + unreadGroupMessages

  return (
    <section className="home-dashboard">
      <div className="home-dashboard-welcome">
        <div className="home-dashboard-welcome-copy">
          <p className="home-dashboard-eyebrow mb-2">
            Communication Platform
          </p>
          <h1 className="home-dashboard-title mb-2">
            {currentUser
              ? `Welcome back, ${currentUser.username}`
              : 'Welcome back'}
          </h1>
          <p className="home-dashboard-subtitle mb-0">
            Pick up a conversation, check requests, or jump into voice.
          </p>
        </div>

        {currentUser && (
          <Avatar
            user={currentUser}
            size="xl"
            className="home-dashboard-avatar"
          />
        )}
      </div>

      <div className="home-dashboard-summary">
        <div>
          <div className="home-dashboard-summary-label">
            Activity
          </div>
          <div className="home-dashboard-summary-value">
            {totalAttention === 0
              ? 'You’re all caught up.'
              : `${totalAttention} item${totalAttention === 1 ? '' : 's'} need your attention.`}
          </div>
        </div>

        <div className="home-dashboard-quick-actions">
          <Link
            className="btn btn-primary btn-sm"
            to="/messages"
          >
            Open DMs
          </Link>
          <Link
            className="btn btn-outline-primary btn-sm"
            to="/voice"
          >
            Voice Rooms
          </Link>
        </div>
      </div>

      <div className="home-dashboard-grid">
        <DashboardCard
          to="/messages"
          label="Direct Messages"
          description={
            unreadDirectMessages > 0
              ? 'You have unread conversations.'
              : 'Continue one-to-one conversations.'
          }
          count={unreadDirectMessages}
          countLabel="unread direct messages"
          icon="✉"
        />

        <DashboardCard
          to="/groups"
          label="Group Chats"
          description={
            groupActivity > 0
              ? 'Messages or invitations are waiting.'
              : 'Stay in sync with your groups.'
          }
          count={groupActivity}
          countLabel="group chat activity items"
          icon="#"
        />

        <DashboardCard
          to="/friends"
          label="Friends"
          description={
            pendingFriendRequests > 0
              ? 'Friend requests are waiting.'
              : 'Find people and manage friendships.'
          }
          count={pendingFriendRequests}
          countLabel="pending friend requests"
          icon="☺"
        />

        <DashboardCard
          to="/voice"
          label="Voice Rooms"
          description={
            pendingVoiceRoomInvitations > 0
              ? 'You have room invitations.'
              : 'Join persistent voice spaces.'
          }
          count={pendingVoiceRoomInvitations}
          countLabel="pending Voice Room invitations"
          icon="◉"
        />
      </div>

      <section className="home-dashboard-help directory-surface">
        <div>
          <h2 className="directory-section-title">
            Your account
          </h2>
          <p className="directory-section-subtitle mb-0">
            Update your avatar or review your account details.
          </p>
        </div>

        <Link
          className="btn btn-sm btn-outline-secondary"
          to="/account"
        >
          Open account
        </Link>
      </section>
    </section>
  )
}


export default HomePage
