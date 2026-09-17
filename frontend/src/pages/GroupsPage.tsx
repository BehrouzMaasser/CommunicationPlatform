import {
  useCallback,
  useEffect,
  useState,
} from 'react'
import {
  Outlet,
  useMatch,
  useNavigate,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { useActivity } from '../activity/useActivity'
import {
  acceptGroupInvitation,
  createGroup,
  getGroups,
  getIncomingGroupInvitations,
  rejectGroupInvitation,
} from '../api/groups'
import GroupConversationList from '../components/groups/GroupConversationList'
import { useRealtimeEvent } from '../realtime/RealtimeContext'
import type { MessageCreatedPayload } from '../realtime/messageEvents'

import type {
  GroupConversation,
  GroupInvitation,
} from '../types/groups'


function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }
  return error instanceof Error
    ? error.message
    : 'Something went wrong.'
}


function GroupsPage() {
  const navigate = useNavigate()
  const activeGroupMatch =
    useMatch(
      '/groups/:groupId/messages',
    )

  const {
    getGroupUnread,
    refreshActivity,
  } = useActivity()

  const [groups, setGroups] =
    useState<GroupConversation[]>([])
  const [invitations, setInvitations] =
    useState<GroupInvitation[]>([])
  const [loading, setLoading] =
    useState(true)
  const [busy, setBusy] =
    useState<string | null>(null)
  const [error, setError] =
    useState<string | null>(null)

  const refresh =
    useCallback(
      async () => {
        const [
          groupData,
          invitationData,
        ] = await Promise.all([
          getGroups(),
          getIncomingGroupInvitations(),
        ])

        setGroups(groupData)
        setInvitations(
          invitationData,
        )
      },
      [],
    )

  const refreshGroups =
    useCallback(
      async () => {
        setGroups(
          await getGroups(),
        )
      },
      [],
    )

  const handleRealtimeChange =
    useCallback(
      () => {
        void refresh()
      },
      [refresh],
    )

  const handleMessageCreated =
    useCallback(
      ({ payload }: {
        payload: MessageCreatedPayload
      }) => {
        if (
          payload.conversation_type
          === 'group'
        ) {
          void refreshGroups()
        }
      },
      [refreshGroups],
    )

  useRealtimeEvent(
    'message.created',
    handleMessageCreated,
  )
  useRealtimeEvent(
    'group_invitation.created',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group_invitation.accepted',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group_invitation.rejected',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group_invitation.cancelled',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.member_added',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.member_removed',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.member_left',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.renamed',
    handleRealtimeChange,
  )
  useRealtimeEvent(
    'group.deleted',
    handleRealtimeChange,
  )

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [groupData, invitationData] =
          await Promise.all([
            getGroups(),
            getIncomingGroupInvitations(),
          ])

        if (!cancelled) {
          setGroups(groupData)
          setInvitations(invitationData)
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(errorText(requestError))
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
    name: string,
  ) {
    setBusy('create')
    setError(null)

    try {
      const group =
        await createGroup(name)

      setGroups(
        (current) => [
          group,
          ...current.filter(
            (item) =>
              item.id !== group.id,
          ),
        ],
      )

      navigate(
        `/groups/${group.id}/messages`,
      )
      return true
    } catch (requestError) {
      setError(errorText(requestError))
      return false
    } finally {
      setBusy(null)
    }
  }

  async function handleInvitation(
    invitationId: number,
    action: 'accept' | 'reject',
  ) {
    const key =
      `${action}-${invitationId}`

    setBusy(key)
    setError(null)

    try {
      if (action === 'accept') {
        await acceptGroupInvitation(
          invitationId,
        )
      } else {
        await rejectGroupInvitation(
          invitationId,
        )
      }

      await Promise.all([
        refresh(),
        refreshActivity(),
      ])
    } catch (requestError) {
      setError(errorText(requestError))
    } finally {
      setBusy(null)
    }
  }

  if (loading) {
    return (
      <div className="dm-page-loading">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading group chats"
        />
      </div>
    )
  }

  return (
    <section
      className={`group-chats-page${activeGroupMatch ? ' has-active-conversation' : ''}`}
    >
      <aside
        className="group-chats-list-pane"
        aria-label="Group chat conversations"
      >
        <GroupConversationList
          groups={groups}
          invitations={invitations}
          getUnread={getGroupUnread}
          creating={busy === 'create'}
          invitationBusyKey={
            busy === 'create'
              ? null
              : busy
          }
          actionError={error}
          onCreate={handleCreate}
          onInvitation={handleInvitation}
        />
      </aside>

      <main className="group-chats-content-pane">
        <Outlet />
      </main>
    </section>
  )
}


export default GroupsPage
