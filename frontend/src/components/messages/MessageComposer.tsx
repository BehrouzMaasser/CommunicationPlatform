import {
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'

import type {
  Message,
  MessageDraft,
} from '../../types/messages'

import EmojiPicker from './EmojiPicker'


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
  onTyping?: () => void
  onTypingStop?: () => void
}


function MessageComposer({
  placeholder,
  replyingTo,
  onCancelReply,
  onSend,
  disabled = false,
  disabledMessage,
  onTyping,
  onTypingStop,
}: MessageComposerProps) {
  const fileInputRef =
    useRef<HTMLInputElement | null>(
      null,
    )

  const textareaRef =
    useRef<HTMLTextAreaElement | null>(
      null,
    )

  const emojiPickerContainerRef =
    useRef<HTMLDivElement | null>(
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

  const [emojiPickerOpen, setEmojiPickerOpen] =
    useState(false)

  function handleTextChange(
    value: string,
  ) {
    setMessageText(value)

    if (value.trim()) {
      onTyping?.()
    } else {
      onTypingStop?.()
    }
  }


  function insertEmoji(
    emoji: string,
  ) {
    const textarea = textareaRef.current
    const selectionStart =
      textarea?.selectionStart
      ?? messageText.length
    const selectionEnd =
      textarea?.selectionEnd
      ?? selectionStart

    const nextValue =
      messageText.slice(
        0,
        selectionStart,
      )
      + emoji
      + messageText.slice(
          selectionEnd,
        )

    const nextCursorPosition =
      selectionStart
      + emoji.length

    handleTextChange(nextValue)

    window.requestAnimationFrame(
      () => {
        const currentTextarea =
          textareaRef.current

        if (!currentTextarea) {
          return
        }

        currentTextarea.focus()
        currentTextarea.setSelectionRange(
          nextCursorPosition,
          nextCursorPosition,
        )
      },
    )
  }

  useEffect(
    () => () => {
      onTypingStop?.()
    },
    [onTypingStop],
  )


  useEffect(() => {
    if (!emojiPickerOpen) {
      return
    }

    function handlePointerDown(
      event: PointerEvent,
    ) {
      const target =
        event.target

      if (
        !(target instanceof Node)
        || emojiPickerContainerRef.current?.contains(
          target,
        )
      ) {
        return
      }

      setEmojiPickerOpen(false)
    }

    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (event.key === 'Escape') {
        setEmojiPickerOpen(false)
        textareaRef.current?.focus()
      }
    }

    document.addEventListener(
      'pointerdown',
      handlePointerDown,
    )
    document.addEventListener(
      'keydown',
      handleKeyDown,
    )

    return () => {
      document.removeEventListener(
        'pointerdown',
        handlePointerDown,
      )
      document.removeEventListener(
        'keydown',
        handleKeyDown,
      )
    }
  }, [emojiPickerOpen])

  useEffect(() => {
    if (disabled) {
      onTypingStop?.()
    }
  }, [
    disabled,
    onTypingStop,
  ])

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

  function handleMessageKeyDown(
    event:
      ReactKeyboardEvent<HTMLTextAreaElement>,
  ) {
    if (
      event.key !== 'Enter' ||
      event.shiftKey ||
      event.nativeEvent.isComposing
    ) {
      return
    }

    event.preventDefault()
    event.currentTarget.form?.requestSubmit()
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

    let sentSuccessfully = false

    try {
      await onSend({
        content: messageText,
        replyToId:
          replyingTo?.id,
        files: selectedFiles,
      })

      onTypingStop?.()
      setEmojiPickerOpen(false)
      clearComposer()
      sentSuccessfully = true
    } catch (requestError) {
      setError(
        describeError(
          requestError,
        ),
      )
    } finally {
      setSending(false)

      if (sentSuccessfully) {
        window.requestAnimationFrame(
          () => {
            textareaRef.current?.focus()
          },
        )
      }
    }
  }

  const isEmojiPickerVisible =
    emojiPickerOpen && !disabled

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
        className="message-composer-form"
        onSubmit={handleSubmit}
      >
        <textarea
          className="form-control mb-2"
          ref={textareaRef}
          rows={2}
          value={messageText}
          onChange={(event) =>
            handleTextChange(
              event.target.value,
            )
          }
          onKeyDown={
            handleMessageKeyDown
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
          <div className="d-flex align-items-center gap-2">
            <div
              className="emoji-picker-shell"
              ref={emojiPickerContainerRef}
            >
              <button
                className="btn btn-outline-secondary emoji-toggle-button"
                type="button"
                aria-label="Add emoji"
                aria-expanded={isEmojiPickerVisible}
                disabled={
                  sending ||
                  disabled
                }
                onClick={() =>
                  setEmojiPickerOpen(
                    (current) => !current,
                  )
                }
              >
                <span aria-hidden="true">😊</span>
                <span className="d-none d-sm-inline ms-1">
                  Emoji
                </span>
              </button>

              {isEmojiPickerVisible && (
                <EmojiPicker
                  onSelect={insertEmoji}
                />
              )}
            </div>

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
