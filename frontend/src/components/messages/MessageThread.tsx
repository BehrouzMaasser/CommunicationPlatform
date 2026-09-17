import {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'

import { useRealtime } from '../../realtime/RealtimeContext'

import AttachmentViewer from './AttachmentViewer'

import type {
  Message,
  MessageAttachment,
  MessageReply,
} from '../../types/messages'


const BOTTOM_THRESHOLD_PX = 80


function formatMessageTime(
  value: string,
): string {
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


function formatFileSize(
  bytes: number,
): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  const kilobytes = bytes / 1024

  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`
  }

  const megabytes =
    kilobytes / 1024

  return `${megabytes.toFixed(1)} MB`
}


function getReplySummary(
  reply: MessageReply,
): string {
  if (reply.content.trim()) {
    return reply.content
  }

  if (
    reply.attachments.length === 1
  ) {
    return `Attachment: ${reply.attachments[0].original_filename}`
  }

  if (
    reply.attachments.length > 1
  ) {
    return `${reply.attachments.length} attachments`
  }

  return 'Message'
}


function AttachmentButton({
  attachment,
  onOpen,
}: {
  attachment: MessageAttachment
  onOpen: (
    attachment: MessageAttachment,
  ) => void
}) {
  return (
    <button
      className="message-attachment-open border rounded p-2 d-flex justify-content-between align-items-center gap-3 w-100 text-start"
      type="button"
      onClick={() => {
        onOpen(attachment)
      }}
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
    </button>
  )
}



type MessageThreadProps = {
  messages: Message[]
  hasOlderMessages?: boolean
  loadingOlderMessages?: boolean
  olderMessagesError?: string | null
  onLoadOlderMessages?: () => Promise<void>
  onReply?: (
    message: Message,
  ) => void
  onAtBottomChange?: (
    isAtBottom: boolean,
  ) => void
}


function MessageThread({
  messages,
  hasOlderMessages = false,
  loadingOlderMessages = false,
  olderMessagesError = null,
  onLoadOlderMessages,
  onReply,
  onAtBottomChange,
}: MessageThreadProps) {
  const {
    currentUserId,
  } = useRealtime()

  const [
    openAttachment,
    setOpenAttachment,
  ] = useState<MessageAttachment | null>(
    null,
  )

  const viewportRef =
    useRef<HTMLDivElement | null>(
      null,
    )

  const hasInitialPositionRef =
    useRef(false)

  const isNearBottomRef =
    useRef(true)

  const previousLastMessageIdRef =
    useRef<number | null>(null)

  const [newMessagesBelow, setNewMessagesBelow] =
    useState(0)

  const reportAtBottom =
    useCallback(
      (isAtBottom: boolean) => {
        onAtBottomChange?.(
          isAtBottom,
        )
      },
      [onAtBottomChange],
    )

  const scrollToBottom =
    useCallback(
      (
        behavior:
          ScrollBehavior,
      ) => {
        const viewport =
          viewportRef.current

        if (!viewport) {
          return
        }

        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior,
        })

        isNearBottomRef.current = true
        setNewMessagesBelow(0)

        if (behavior === 'auto') {
          reportAtBottom(true)
        }
      },
      [reportAtBottom],
    )

  async function handleLoadOlderMessages() {
    if (
      !onLoadOlderMessages
      || loadingOlderMessages
    ) {
      return
    }

    const viewport = viewportRef.current
    const previousScrollHeight =
      viewport?.scrollHeight ?? 0
    const previousScrollTop =
      viewport?.scrollTop ?? 0

    await onLoadOlderMessages()

    window.requestAnimationFrame(() => {
      const currentViewport =
        viewportRef.current

      if (!currentViewport) {
        return
      }

      const addedHeight =
        currentViewport.scrollHeight
        - previousScrollHeight

      currentViewport.scrollTop =
        previousScrollTop
        + Math.max(addedHeight, 0)
    })
  }


  function handleScroll() {
    const viewport =
      viewportRef.current

    if (!viewport) {
      return
    }

    const distanceFromBottom =
      viewport.scrollHeight
      - viewport.scrollTop
      - viewport.clientHeight

    const isNearBottom =
      distanceFromBottom <=
      BOTTOM_THRESHOLD_PX

    if (
      isNearBottom !==
      isNearBottomRef.current
    ) {
      isNearBottomRef.current =
        isNearBottom
      reportAtBottom(
        isNearBottom,
      )
    }

    if (isNearBottom) {
      setNewMessagesBelow(0)
    }
  }

  useLayoutEffect(() => {
    if (messages.length === 0) {
      hasInitialPositionRef.current =
        false
      previousLastMessageIdRef.current =
        null
      isNearBottomRef.current = true
      reportAtBottom(true)
      return
    }

    const lastMessage =
      messages[
        messages.length - 1
      ]

    const previousLastMessageId =
      previousLastMessageIdRef.current

    if (
      !hasInitialPositionRef.current
    ) {
      hasInitialPositionRef.current =
        true
      previousLastMessageIdRef.current =
        lastMessage.id
      scrollToBottom('auto')
      return
    }

    if (
      previousLastMessageId ===
      lastMessage.id
    ) {
      return
    }

    const previousLastIndex =
      previousLastMessageId === null
        ? -1
        : messages.findIndex(
            (message) =>
              message.id ===
              previousLastMessageId,
          )

    const appendedMessageCount =
      previousLastIndex >= 0
        ? messages.length
          - previousLastIndex
          - 1
        : 1

    previousLastMessageIdRef.current =
      lastMessage.id

    const sentByCurrentUser =
      currentUserId !== null
      && lastMessage.sender.id ===
        currentUserId

    if (
      isNearBottomRef.current
      || sentByCurrentUser
    ) {
      scrollToBottom('smooth')
      return
    }

    setNewMessagesBelow(
      (current) =>
        current
        + Math.max(
            appendedMessageCount,
            1,
          ),
    )
  }, [
    currentUserId,
    messages,
    reportAtBottom,
    scrollToBottom,
  ])

  return (
    <div className="message-thread-shell position-relative">
      <div
        className="message-thread-viewport"
        ref={viewportRef}
        onScroll={handleScroll}
      >
        {hasOlderMessages && (
          <div className="text-center pb-3">
            <button
              className="btn btn-sm btn-outline-secondary"
              type="button"
              disabled={loadingOlderMessages}
              onClick={() => {
                void handleLoadOlderMessages()
              }}
            >
              {loadingOlderMessages
                ? 'Loading older messages…'
                : 'Load older messages'}
            </button>
          </div>
        )}

        {olderMessagesError && (
          <div className="alert alert-warning py-2 small" role="alert">
            {olderMessagesError}
          </div>
        )}

        {messages.length === 0 ? (
          <div className="message-thread-empty text-center py-5">
            <h2 className="h5">
              No messages yet
            </h2>

            <p className="text-secondary mb-0">
              Send the first message below.
            </p>
          </div>
        ) : (
          <div className="d-flex flex-column gap-3 pe-1">
            {messages.map((message) => {
              const sentByCurrentUser =
                message.sender.id ===
                currentUserId

              const deliveredCount =
                message.receipts.filter(
                  (receipt) =>
                    receipt.delivered_at
                    !== null,
                ).length

              const readCount =
                message.receipts.filter(
                  (receipt) =>
                    receipt.read_at
                    !== null,
                ).length

              const showReceiptState =
                sentByCurrentUser
                && message.receipts.length > 0

              return (
                <div
                  className={`message-row d-flex ${sentByCurrentUser ? 'justify-content-start' : 'justify-content-end'}`}
                  key={message.id}
                >
                  <article
                    className={`message-bubble ${sentByCurrentUser ? 'message-bubble-own' : 'message-bubble-other'}`}
                  >
                    {message.reply_to && (
                      <div className="message-reply-preview">
                        <div className="small fw-semibold">
                          Reply to @{message.reply_to.sender.username}
                        </div>

                        <div className="small message-text">
                          {getReplySummary(
                            message.reply_to,
                          )}
                        </div>
                      </div>
                    )}

                    <div className="message-meta d-flex justify-content-between align-items-baseline gap-3 mb-2">
                      <strong className="message-sender">
                        {sentByCurrentUser
                          ? 'You'
                          : `@${message.sender.username}`}
                      </strong>

                      <span className="small text-secondary text-nowrap">
                        {formatMessageTime(
                          message.created_at,
                        )}
                      </span>
                    </div>

                    {message.content && (
                      <p className="message-text mb-0">
                        {message.content}
                      </p>
                    )}

                    {message.attachments.length > 0 && (
                      <div className="mt-3 d-flex flex-column gap-2">
                        {message.attachments.map(
                          (attachment) => (
                            <AttachmentButton
                              attachment={attachment}
                              key={attachment.id}
                              onOpen={setOpenAttachment}
                            />
                          ),
                        )}
                      </div>
                    )}

                    {(onReply || showReceiptState) && (
                      <div
                        className={`message-actions-row d-flex align-items-center gap-3 mt-2 ${onReply ? 'justify-content-between' : 'justify-content-end'}`}
                      >
                        {onReply && (
                          <button
                            className="btn btn-sm btn-link px-0 py-0"
                            type="button"
                            onClick={() =>
                              onReply(message)
                            }
                          >
                            Reply
                          </button>
                        )}

                        {showReceiptState && (
                          <span className="message-receipt-state small text-secondary text-nowrap">
                            Delivered {deliveredCount}
                            {' · '}
                            Read {readCount}
                          </span>
                        )}
                      </div>
                    )}
                  </article>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {messages.length > 0 &&
        newMessagesBelow > 0 && (
        <button
          className="btn btn-primary btn-sm message-thread-new-button shadow"
          type="button"
          onClick={() =>
            scrollToBottom(
              'smooth',
            )
          }
          aria-label={`Jump to ${newMessagesBelow} new ${newMessagesBelow === 1 ? 'message' : 'messages'}`}
        >
          ↓ {newMessagesBelow}{' '}
          {newMessagesBelow === 1
            ? 'new message'
            : 'new messages'}
        </button>
      )}

      {openAttachment && (
        <AttachmentViewer
          attachment={openAttachment}
          onClose={() => {
            setOpenAttachment(null)
          }}
        />
      )}
    </div>
  )
}


export default MessageThread
