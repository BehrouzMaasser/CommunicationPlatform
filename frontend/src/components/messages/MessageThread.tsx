import type {
  Message,
  MessageAttachment,
  MessageReply,
} from '../../types/messages'


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


type MessageThreadProps = {
  messages: Message[]
  onReply?: (
    message: Message,
  ) => void
}


function MessageThread({
  messages,
  onReply,
}: MessageThreadProps) {
  if (messages.length === 0) {
    return (
      <div className="text-center py-5">
        <h2 className="h5">
          No messages yet
        </h2>

        <p className="text-secondary mb-0">
          Send the first message below.
        </p>
      </div>
    )
  }

  return (
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

          {onReply && (
            <div className="mt-3">
              <button
                className="btn btn-sm btn-link px-0"
                type="button"
                onClick={() =>
                  onReply(message)
                }
              >
                Reply
              </button>
            </div>
          )}
        </article>
      ))}
    </div>
  )
}


export default MessageThread
