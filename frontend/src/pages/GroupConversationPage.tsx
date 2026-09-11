import {
  useEffect,
  useState,
} from 'react'
import {
  Link,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { getGroup } from '../api/groups'
import {
  getGroupMessages,
  sendGroupMessage,
} from '../api/messages'

import MessageComposer from '../components/messages/MessageComposer'
import MessageThread from '../components/messages/MessageThread'

import type {
  GroupConversation,
} from '../types/groups'
import type {
  Message,
  MessageDraft,
} from '../types/messages'


function describeError(
  error: unknown,
): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return 'This group does not exist or you are not a current member.'
    }

    if (error.status === 401) {
      return 'Your session is not authenticated. Please sign in again.'
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}


function GroupConversationPage() {
  const { groupId } =
    useParams<{
      groupId: string
    }>()

  const parsedGroupId =
    Number(groupId)

  const [group, setGroup] =
    useState<GroupConversation | null>(
      null,
    )

  const [messages, setMessages] =
    useState<Message[]>([])

  const [
    replyingTo,
    setReplyingTo,
  ] =
    useState<Message | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (
        !Number.isInteger(
          parsedGroupId,
        ) ||
        parsedGroupId <= 0
      ) {
        setError(
          'Invalid group id.',
        )
        setLoading(false)
        return
      }

      try {
        const [
          groupResult,
          messagesResult,
        ] = await Promise.all([
          getGroup(
            parsedGroupId,
          ),
          getGroupMessages(
            parsedGroupId,
          ),
        ])

        if (cancelled) {
          return
        }

        setGroup(groupResult)
        setMessages(
          messagesResult,
        )
      } catch (requestError) {
        if (!cancelled) {
          setError(
            describeError(
              requestError,
            ),
          )
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
  }, [parsedGroupId])

  async function handleSend(
    input: MessageDraft,
  ) {
    const createdMessage =
      await sendGroupMessage(
        parsedGroupId,
        input,
      )

    setMessages((current) => [
      ...current,
      createdMessage,
    ])

    setReplyingTo(null)
  }

  if (loading) {
    return (
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading group chat"
        />
      </div>
    )
  }

  if (
    error ||
    !group
  ) {
    return (
      <section>
        <Link
          className="btn btn-link px-0 mb-3"
          to="/groups"
        >
          ← Back to groups
        </Link>

        <div className="alert alert-danger">
          {error ??
            'Group not found.'}
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="d-flex justify-content-between align-items-center gap-3 mb-3">
        <Link
          className="btn btn-link px-0"
          to={`/groups/${group.id}`}
        >
          ← Group details
        </Link>

        <Link
          className="btn btn-outline-secondary btn-sm"
          to="/groups"
        >
          All groups
        </Link>
      </div>

      <div className="card shadow-sm">
        <div className="card-header bg-white py-3">
          <h1 className="h4 mb-1">
            {group.name}
          </h1>

          <div className="small text-secondary">
            Group chat · Group #{group.id}
          </div>
        </div>

        <div
          className="card-body"
          style={{
            minHeight: '420px',
          }}
        >
          <MessageThread
            messages={messages}
            onReply={(message) =>
              setReplyingTo(
                message,
              )
            }
          />
        </div>

        <div className="card-footer bg-white py-3">
          <MessageComposer
            placeholder={`Message ${group.name}`}
            replyingTo={replyingTo}
            onCancelReply={() =>
              setReplyingTo(null)
            }
            onSend={handleSend}
          />
        </div>
      </div>
    </section>
  )
}


export default GroupConversationPage
