import {
  type ChangeEvent,
  type FormEvent,
  useRef,
  useState,
} from 'react'

import type {
  Message,
  MessageDraft,
} from '../../types/messages'


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


function getMessageSummary(
  message: Message,
): string {
  if (message.content.trim()) {
    return message.content
  }

  if (
    message.attachments.length === 1
  ) {
    return `Attachment: ${message.attachments[0].original_filename}`
  }

  if (
    message.attachments.length > 1
  ) {
    return `${message.attachments.length} attachments`
  }

  return 'Message'
}


function describeError(
  error: unknown,
): string {
  if (error instanceof Error) {
    return error.message
  }

  return 'Could not send message.'
}


type MessageComposerProps = {
  placeholder: string
  replyingTo: Message | null
  onCancelReply: () => void
  onSend: (
    input: MessageDraft,
  ) => Promise<void>
  disabled?: boolean
  disabledMessage?: string
}


function MessageComposer({
  placeholder,
  replyingTo,
  onCancelReply,
  onSend,
  disabled = false,
  disabledMessage,
}: MessageComposerProps) {
  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null,
    )

  const [
    messageText,
    setMessageText,
  ] = useState('')

  const [
    selectedFiles,
    setSelectedFiles,
  ] = useState<File[]>([])

  const [sending, setSending] =
    useState(false)

  const [error, setError] =
    useState<string | null>(null)

  function handleFileSelection(
    event:
      ChangeEvent<HTMLInputElement>,
  ) {
    setSelectedFiles(
      Array.from(
        event.target.files ?? [],
      ),
    )
  }

  function removeSelectedFile(
    indexToRemove: number,
  ) {
    setSelectedFiles(
      (current) =>
        current.filter(
          (_, index) =>
            index !== indexToRemove,
        ),
    )
  }

  function clearComposer() {
    setMessageText('')
    setSelectedFiles([])

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  async function handleSubmit(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    const hasText =
      Boolean(messageText.trim())

    const hasFiles =
      selectedFiles.length > 0

    if (
      disabled ||
      (!hasText && !hasFiles)
    ) {
      return
    }

    setSending(true)
    setError(null)

    try {
      await onSend({
        content: messageText,
        replyToId:
          replyingTo?.id,
        files: selectedFiles,
      })

      clearComposer()
    } catch (requestError) {
      setError(
        describeError(
          requestError,
        ),
      )
    } finally {
      setSending(false)
    }
  }

  const canSend =
    !disabled &&
    (
      Boolean(
        messageText.trim(),
      ) ||
      selectedFiles.length > 0
    )

  return (
    <>
      {disabled &&
        disabledMessage && (
          <div className="alert alert-secondary mb-3">
            {disabledMessage}
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
            disabled={sending}
            onClick={
              onCancelReply
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
                    disabled={sending}
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

      {error && (
        <div className="alert alert-danger py-2">
          {error}
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
              : placeholder
          }
          disabled={
            sending ||
            disabled
          }
        />

        <div className="d-flex flex-column flex-sm-row justify-content-between gap-2">
          <div>
            <label
              className={`btn btn-outline-secondary${disabled ? ' disabled' : ''}`}
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
              onChange={
                handleFileSelection
              }
              disabled={
                sending ||
                disabled
              }
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
    </>
  )
}


export default MessageComposer
