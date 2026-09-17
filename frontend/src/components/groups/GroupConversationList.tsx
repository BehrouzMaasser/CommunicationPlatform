import {
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useMemo,
  useState,
} from 'react'
import {
  NavLink,
} from 'react-router-dom'

import type {
  GroupConversation,
  GroupInvitation,
} from '../../types/groups'

import GroupAvatar from './GroupAvatar'


type GroupConversationListProps = {
  groups: GroupConversation[]
  invitations: GroupInvitation[]
  getUnread: (
    groupId: number,
  ) => number
  creating: boolean
  invitationBusyKey: string | null
  actionError: string | null
  onCreate: (
    name: string,
  ) => Promise<boolean>
  onInvitation: (
    invitationId: number,
    action: 'accept' | 'reject',
  ) => Promise<void>
}


function formatActivity(
  value: string,
): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate()

  if (sameDay) {
    return new Intl.DateTimeFormat(
      undefined,
      {
        hour: 'numeric',
        minute: '2-digit',
      },
    ).format(date)
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      month: 'short',
      day: 'numeric',
    },
  ).format(date)
}


function submitOnEnter(
  event: ReactKeyboardEvent<HTMLInputElement>,
) {
  if (
    event.key !== 'Enter'
    || event.nativeEvent.isComposing
    || event.shiftKey
    || event.altKey
    || event.ctrlKey
    || event.metaKey
  ) {
    return
  }

  const form = event.currentTarget.form
  const submitButton =
    form?.querySelector<HTMLButtonElement>(
      'button[type="submit"]',
    )

  if (!form || submitButton?.disabled) {
    return
  }

  event.preventDefault()
  form.requestSubmit()
}


function GroupConversationList({
  groups,
  invitations,
  getUnread,
  creating,
  invitationBusyKey,
  actionError,
  onCreate,
  onInvitation,
}: GroupConversationListProps) {
  const [searchQuery, setSearchQuery] =
    useState('')
  const [createOpen, setCreateOpen] =
    useState(false)
  const [name, setName] =
    useState('')

  const normalizedQuery =
    searchQuery.trim().toLocaleLowerCase()

  const filteredGroups =
    useMemo(
      () => {
        if (!normalizedQuery) {
          return groups
        }

        return groups.filter(
          (group) =>
            group.name
              .toLocaleLowerCase()
              .includes(
                normalizedQuery,
              ),
        )
      },
      [groups, normalizedQuery],
    )

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const trimmedName = name.trim()

    if (!trimmedName || creating) {
      return
    }

    const created =
      await onCreate(trimmedName)

    if (created) {
      setName('')
      setCreateOpen(false)
    }
  }

  return (
    <div className="dm-list-shell group-list-shell">
      <div className="dm-list-header">
        <div className="min-width-0">
          <h1 className="dm-list-title mb-0">
            Group Chats
          </h1>
          <div className="dm-list-subtitle">
            {groups.length}{' '}
            {groups.length === 1
              ? 'group'
              : 'groups'}
          </div>
        </div>

        <button
          className={`dm-new-message-button${createOpen ? ' is-active' : ''}`}
          type="button"
          aria-label={
            createOpen
              ? 'Close create group panel'
              : 'Create group chat'
          }
          aria-expanded={createOpen}
          title="Create group chat"
          onClick={() => {
            setCreateOpen(
              (current) => !current,
            )
          }}
        >
          <span aria-hidden="true">
            {createOpen ? '×' : '+'}
          </span>
        </button>
      </div>

      <div className="dm-list-search-wrap">
        <label
          className="visually-hidden"
          htmlFor="group-conversation-search"
        >
          Search group chats
        </label>
        <input
          id="group-conversation-search"
          className="form-control dm-list-search"
          type="search"
          value={searchQuery}
          placeholder="Search groups"
          autoComplete="off"
          onChange={(event) => {
            setSearchQuery(
              event.target.value,
            )
          }}
        />
      </div>

      {actionError && (
        <div
          className="alert alert-danger py-2 mx-3 mt-2 mb-0 small"
          role="alert"
        >
          {actionError}
        </div>
      )}

      {createOpen && (
        <section
          className="dm-new-message-panel"
          aria-label="Create group chat"
        >
          <div className="dm-new-message-heading">
            New group chat
          </div>

          <form
            className="d-flex gap-2"
            onSubmit={handleSubmit}
          >
            <input
              className="form-control form-control-sm"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
              }}
              onKeyDown={submitOnEnter}
              placeholder="Group name"
              autoFocus
            />

            <button
              className="btn btn-sm btn-primary text-nowrap"
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
        </section>
      )}

      {invitations.length > 0 && (
        <section
          className="group-list-invitations"
          aria-label="Group invitations"
        >
          <div className="group-list-section-heading">
            Invitations
            <span className="group-list-section-count">
              {invitations.length}
            </span>
          </div>

          <div className="group-list-invitation-items">
            {invitations.map(
              (invitation) => {
                const accepting =
                  invitationBusyKey
                  === `accept-${invitation.id}`
                const rejecting =
                  invitationBusyKey
                  === `reject-${invitation.id}`

                return (
                  <div
                    className="group-list-invitation"
                    key={invitation.id}
                  >
                    <GroupAvatar
                      name={invitation.group.name}
                      avatarUrl={invitation.group.avatar_url}
                      size="sm"
                    />

                    <div className="group-list-invitation-copy">
                      <div className="group-list-invitation-name">
                        {invitation.group.name}
                      </div>
                      <div className="group-list-invitation-meta">
                        Invited by @{invitation.invited_by.username}
                      </div>
                    </div>

                    <div className="group-list-invitation-actions">
                      <button
                        className="btn btn-sm btn-primary"
                        type="button"
                        disabled={
                          invitationBusyKey
                          !== null
                        }
                        onClick={() => {
                          void onInvitation(
                            invitation.id,
                            'accept',
                          )
                        }}
                      >
                        {accepting
                          ? '…'
                          : 'Accept'}
                      </button>

                      <button
                        className="btn btn-sm btn-outline-secondary"
                        type="button"
                        aria-label={`Reject invitation to ${invitation.group.name}`}
                        title="Reject"
                        disabled={
                          invitationBusyKey
                          !== null
                        }
                        onClick={() => {
                          void onInvitation(
                            invitation.id,
                            'reject',
                          )
                        }}
                      >
                        {rejecting
                          ? '…'
                          : '×'}
                      </button>
                    </div>
                  </div>
                )
              },
            )}
          </div>
        </section>
      )}

      <div
        className="dm-conversation-list group-conversation-list"
        role="list"
      >
        {groups.length === 0 ? (
          <div className="dm-list-empty">
            <div className="dm-list-empty-icon" aria-hidden="true">
              #
            </div>
            <div className="fw-semibold">
              No group chats yet
            </div>
            <p className="small text-secondary mb-0">
              Create one with the + button or accept an invitation.
            </p>
          </div>
        ) : filteredGroups.length === 0 ? (
          <div className="dm-list-empty">
            <div className="fw-semibold">
              No matches
            </div>
            <p className="small text-secondary mb-0">
              Try a different group name.
            </p>
          </div>
        ) : (
          filteredGroups.map(
            (group) => {
              const unread =
                getUnread(group.id)

              return (
                <NavLink
                  className={({ isActive }) =>
                    `dm-conversation-list-item group-conversation-list-item${isActive ? ' active' : ''}`
                  }
                  key={group.id}
                  to={`/groups/${group.id}/messages`}
                  role="listitem"
                >
                  <GroupAvatar
                    name={group.name}
                    avatarUrl={group.avatar_url}
                    size="md"
                  />

                  <span className="dm-conversation-copy">
                    <span className="dm-conversation-row-top">
                      <span className="dm-conversation-name">
                        {group.name}
                      </span>
                      <span className="dm-conversation-time">
                        {formatActivity(
                          group.last_activity_at,
                        )}
                      </span>
                    </span>

                    <span className="dm-conversation-row-bottom group-conversation-row-bottom">
                      <span />

                      {unread > 0 && (
                        <span
                          className="dm-unread-badge"
                          aria-label={`${unread} unread messages`}
                        >
                          {unread > 99
                            ? '99+'
                            : unread}
                        </span>
                      )}
                    </span>
                  </span>
                </NavLink>
              )
            },
          )
        )}
      </div>
    </div>
  )
}


export default GroupConversationList
