import {
  type ChangeEvent,
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from 'react'
import {
  Link,
  useParams,
} from 'react-router-dom'

import { ApiError } from '../api/client'
import { getDirectConversation } from '../api/conversations'
import { getFriends } from '../api/friendships'
import {
  getDirectMessages,
  sendDirectMessage,
} from '../api/messages'

import type { DirectConversation } from '../types/conversations'
import type {
  Message,
  MessageAttachment,
  MessageReply,
} from '../types/messages'


function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return 'This direct conversation does not exist or you do not have access to it.'
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


function formatMessageTime(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: 'medium',
      timeStyle: 'short',
    },
  ).format(date)
}


function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  const kilobytes = bytes / 1024

  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`
  }

  const megabytes = kilobytes / 1024

  return `${megabytes.toFixed(1)} MB`
}


function getReplySummary(reply: MessageReply): string {
  if (reply.content.trim()) {
    return reply.content
  }

  if (reply.attachments.length === 1) {
    return `Attachment: ${reply.attachments[0].original_filename}`
  }

  if (reply.attachments.length > 1) {
    return `${reply.attachments.length} attachments`
  }

  return 'Message'
}


function getMessageSummary(message: Message): string {
  if (message.content.trim()) {
    return message.content
  }

  if (message.attachments.length === 1) {
    return `Attachment: ${message.attachments[0].original_filename}`
  }

  if (message.attachments.length > 1) {
    return `${message.attachments.length} attachments`
  }

  return 'Message'
}


function DirectConversationPage() {
  const { conversationId } =
    useParams<{
      conversationId: string
    }>()

  const fileInputRef =
    useRef<HTMLInputElement | null>(null)

  const [conversation, setConversation] =
    useState<DirectConversation | null>(
      null,
    )

  const [messages, setMessages] =
    useState<Message[]>([])

  const [canMessage, setCanMessage] =
    useState(false)

  const [messageText, setMessageText] =
    useState('')

  const [selectedFiles, setSelectedFiles] =
    useState<File[]>([])

  const [replyingTo, setReplyingTo] =
    useState<Message | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [sending, setSending] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)

  const [sendError, setSendError] =
    useState<string | null>(null)

  const parsedConversationId =
    Number(conversationId)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (
        !Number.isInteger(
          parsedConversationId,
        ) ||
        parsedConversationId <= 0
      ) {
        setError(
          'Invalid conversation id.',
        )
        setLoading(false)
        return
      }

      try {
        const [
          conversationResult,
          messagesResult,
          friendsResult,
        ] = await Promise.all([
          getDirectConversation(
            parsedConversationId,
          ),
          getDirectMessages(
            parsedConversationId,
          ),
          getFriends(),
        ])

        if (cancelled) {
          return
        }

        setConversation(
          conversationResult,
        )

        setMessages(
          messagesResult,
        )

        setCanMessage(
          friendsResult.some(
            (friend) =>
              friend.id ===
              conversationResult.other_user.id,
          ),
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
  }, [parsedConversationId])

  function handleFileSelection(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const files = Array.from(
      event.target.files ?? [],
    )

    setSelectedFiles(files)
  }

  function removeSelectedFile(
    indexToRemove: number,
  ) {
    setSelectedFiles((current) =>
      current.filter(
        (_, index) =>
          index !== indexToRemove,
      ),
    )
  }

  function clearComposer() {
    setMessageText('')
    setSelectedFiles([])
    setReplyingTo(null)

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const hasText =
      Boolean(messageText.trim())

    const hasFiles =
      selectedFiles.length > 0

    if (!canMessage) {
      setSendError(
        'You must be friends to send direct messages.',
      )
      return
    }

    if (!hasText && !hasFiles) {
      return
    }

    setSending(true)
    setSendError(null)

    try {
      const createdMessage =
        await sendDirectMessage(
          parsedConversationId,
          {
            content: messageText,
            replyToId:
              replyingTo?.id,
            files: selectedFiles,
          },
        )

      setMessages((current) => [
        ...current,
        createdMessage,
      ])

      clearComposer()
    } catch (requestError) {
      setSendError(
        describeError(
          requestError,
        ),
      )
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="py-5 text-center">
        <div
          className="spinner-border"
          role="status"
          aria-label="Loading conversation"
        />
      </div>
    )
  }

  if (error || !conversation) {
    return (
      <section>
        <Link
          className="btn btn-link px-0 mb-3"
          to="/messages"
        >
          ← Back to messages
        </Link>

        <div className="alert alert-danger">
          {error ?? 'Conversation not found.'}
        </div>
      </section>
    )
  }

  const canSend =
    canMessage &&
    (
      Boolean(messageText.trim()) ||
      selectedFiles.length > 0
    )

  return (
    <section>
      <Link
        className="btn btn-link px-0 mb-3"
        to="/messages"
      >
        ← Back to messages
      </Link>

      <div className="card shadow-sm">
        <div className="card-header bg-white py-3">
          <h1 className="h4 mb-1">
            @{conversation.other_user.username}
          </h1>

          <div className="small text-secondary">
            Direct conversation #{conversation.id}
          </div>
        </div>

        <div
          className="card-body"
          style={{
            minHeight: '420px',
          }}
        >
          {messages.length === 0 ? (
            <div className="text-center py-5">
              <h2 className="h5">
                No messages yet
              </h2>

              <p className="text-secondary mb-0">
                Send the first message below.
              </p>
            </div>
          ) : (
            <div className="d-flex flex-column gap-3">
              {messages.map((message) => (
                <article
                  className="border rounded p-3"
                  key={message.id}
                >
                  {message.reply_to && (
                    <div className="border-start border-3 ps-3 py-1 mb-3 text-secondary">
                      <div className="small fw-semibold">
                        Reply to @{message.reply_to.sender.username}
                      </div>

                      <div className="small text-break">
                        {getReplySummary(
                          message.reply_to,
                        )}
                      </div>
                    </div>
                  )}

                  <div className="d-flex justify-content-between gap-3 mb-2">
                    <strong>
                      @{message.sender.username}
                    </strong>

                    <span className="small text-secondary">
                      {formatMessageTime(
                        message.created_at,
                      )}
                    </span>
                  </div>

                  {message.content && (
                    <p className="mb-0 text-break">
                      {message.content}
                    </p>
                  )}

                  {message.attachments.length > 0 && (
                    <div className="mt-3 d-flex flex-column gap-2">
                      {message.attachments.map(
                        (attachment) => (
                          <AttachmentLink
                            attachment={attachment}
                            key={attachment.id}
                          />
                        ),
                      )}
                    </div>
                  )}

                  <div className="mt-3">
                    <button
                      className="btn btn-sm btn-link px-0"
                      type="button"
                      onClick={() =>
                        setReplyingTo(
                          message,
                        )
                      }
                    >
                      Reply
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        <div className="card-footer bg-white py-3">
          {!canMessage && (
            <div className="alert alert-secondary mb-3">
              You are no longer friends with @{conversation.other_user.username}.
              This conversation remains available as history, but new direct
              messages are disabled.
            </div>
          )}
          {replyingTo && (
            <div className="border rounded bg-light p-2 mb-2 d-flex justify-content-between align-items-start gap-3">
              <div>
                <div className="small fw-semibold">
                  Replying to @{replyingTo.sender.username}
                </div>

                <div className="small text-secondary text-break">
                  {getMessageSummary(
                    replyingTo,
                  )}
                </div>
              </div>

              <button
                className="btn-close"
                type="button"
                aria-label="Cancel reply"
                onClick={() =>
                  setReplyingTo(null)
                }
              />
            </div>
          )}

          {selectedFiles.length > 0 && (
            <div className="border rounded bg-light p-2 mb-2">
              <div className="small fw-semibold mb-2">
                Selected files
              </div>

              <div className="d-flex flex-column gap-2">
                {selectedFiles.map(
                  (file, index) => (
                    <div
                      className="d-flex justify-content-between align-items-center gap-3"
                      key={`${file.name}-${file.lastModified}-${index}`}
                    >
                      <div className="small text-break">
                        {file.name}
                        <span className="text-secondary ms-2">
                          {formatFileSize(
                            file.size,
                          )}
                        </span>
                      </div>

                      <button
                        className="btn btn-sm btn-outline-secondary"
                        type="button"
                        disabled={sending || !canMessage}
                        onClick={() =>
                          removeSelectedFile(
                            index,
                          )
                        }
                      >
                        Remove
                      </button>
                    </div>
                  ),
                )}
              </div>
            </div>
          )}

          {sendError && (
            <div className="alert alert-danger py-2">
              {sendError}
            </div>
          )}

          <form
            onSubmit={handleSubmit}
          >
            <textarea
              className="form-control mb-2"
              rows={2}
              value={messageText}
              onChange={(event) =>
                setMessageText(
                  event.target.value,
                )
              }
              placeholder={
                replyingTo
                  ? `Reply to @${replyingTo.sender.username}`
                  : `Message @${conversation.other_user.username}`
              }
              disabled={sending || !canMessage}
            />

            <div className="d-flex flex-column flex-sm-row justify-content-between gap-2">
              <div>
                <label
                  className="btn btn-outline-secondary"
                  htmlFor="message-attachments"
                >
                  Attach files
                </label>

                <input
                  className="visually-hidden"
                  id="message-attachments"
                  type="file"
                  multiple
                  ref={fileInputRef}
                  onChange={handleFileSelection}
                  disabled={sending || !canMessage}
                />
              </div>

              <button
                className="btn btn-primary px-4"
                type="submit"
                disabled={
                  sending ||
                  !canSend
                }
              >
                {sending
                  ? 'Sending…'
                  : 'Send'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  )
}


function AttachmentLink({
  attachment,
}: {
  attachment: MessageAttachment
}) {
  return (
    <a
      className="border rounded p-2 text-decoration-none d-flex justify-content-between align-items-center gap-3"
      href={attachment.download_url}
    >
      <div className="text-break">
        <div className="fw-semibold">
          {attachment.original_filename}
        </div>

        <div className="small text-secondary">
          {attachment.mime_type}
        </div>
      </div>

      <span className="small text-secondary text-nowrap">
        {formatFileSize(
          attachment.size_bytes,
        )}
      </span>
    </a>
  )
}


export default DirectConversationPage
