import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  getAttachmentFile,
} from '../../api/attachments'
import {
  downloadBrowserBlob,
} from '../../platform/browserFiles'

import type {
  MessageAttachment,
} from '../../types/messages'


type PreviewKind =
  | 'image'
  | 'audio'
  | 'video'
  | 'pdf'
  | 'text'
  | 'unsupported'


type AttachmentViewerProps = {
  attachment: MessageAttachment
  onClose: () => void
}


function previewKindFor(
  mimeType: string,
): PreviewKind {
  const normalized =
    mimeType
      .split(';', 1)[0]
      .trim()
      .toLowerCase()

  if (
    normalized.startsWith('image/')
    && normalized !== 'image/svg+xml'
  ) {
    return 'image'
  }

  if (normalized.startsWith('audio/')) {
    return 'audio'
  }

  if (normalized.startsWith('video/')) {
    return 'video'
  }

  if (normalized === 'application/pdf') {
    return 'pdf'
  }

  if (
    normalized === 'text/plain'
    || normalized === 'text/csv'
    || normalized === 'application/json'
  ) {
    return 'text'
  }

  return 'unsupported'
}


function AttachmentViewer({
  attachment,
  onClose,
}: AttachmentViewerProps) {
  const previewKind =
    useMemo(
      () =>
        previewKindFor(
          attachment.mime_type,
        ),
      [attachment.mime_type],
    )

  const [blob, setBlob] =
    useState<Blob | null>(null)

  const [objectUrl, setObjectUrl] =
    useState<string | null>(null)

  const [textContent, setTextContent] =
    useState<string | null>(null)

  const [error, setError] =
    useState<string | null>(null)

  const [isLoading, setIsLoading] =
    useState(
      previewKind !== 'unsupported',
    )

  const [isDownloading, setIsDownloading] =
    useState(false)

  const dialogRef =
    useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (previewKind === 'unsupported') {
      return
    }

    const controller =
      new AbortController()

    let generatedObjectUrl:
      string | null = null

    async function loadAttachment() {
      try {
        const nextBlob =
          await getAttachmentFile(
            attachment.download_url,
            controller.signal,
          )

        if (controller.signal.aborted) {
          return
        }

        setBlob(nextBlob)

        if (previewKind === 'text') {
          const nextText =
            await nextBlob.text()

          if (
            !controller.signal.aborted
          ) {
            setTextContent(nextText)
          }
        } else {
          generatedObjectUrl =
            URL.createObjectURL(
              nextBlob,
            )

          setObjectUrl(
            generatedObjectUrl,
          )
        }
      } catch (loadError) {
        if (
          loadError instanceof DOMException
          && loadError.name === 'AbortError'
        ) {
          return
        }

        setError(
          loadError instanceof Error
            ? loadError.message
            : 'The attachment could not be loaded.',
        )
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }

    void loadAttachment()

    return () => {
      controller.abort()

      if (generatedObjectUrl) {
        URL.revokeObjectURL(
          generatedObjectUrl,
        )
      }
    }
  }, [
    attachment.download_url,
    previewKind,
  ])

  useEffect(() => {
    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener(
      'keydown',
      handleKeyDown,
    )

    dialogRef.current?.focus()

    return () => {
      document.removeEventListener(
        'keydown',
        handleKeyDown,
      )
    }
  }, [onClose])

  async function handleDownload() {
    if (isDownloading) {
      return
    }

    setIsDownloading(true)
    setError(null)

    try {
      const fileBlob =
        blob
        ?? await getAttachmentFile(
          attachment.download_url,
        )

      downloadBrowserBlob(
        fileBlob,
        attachment.original_filename,
      )
    } catch (downloadError) {
      setError(
        downloadError instanceof Error
          ? downloadError.message
          : 'The attachment could not be downloaded.',
      )
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div
      className="attachment-viewer-backdrop"
      onMouseDown={(event) => {
        if (
          event.target ===
          event.currentTarget
        ) {
          onClose()
        }
      }}
    >
      <div
        className="attachment-viewer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="attachment-viewer-title"
        tabIndex={-1}
        ref={dialogRef}
      >
        <div className="attachment-viewer-header">
          <div className="flex-grow-1 overflow-hidden">
            <h2
              className="h5 mb-1 text-break"
              id="attachment-viewer-title"
            >
              {attachment.original_filename}
            </h2>
            <div className="small text-secondary">
              {attachment.mime_type}
            </div>
          </div>

          <button
            className="btn-close flex-shrink-0"
            type="button"
            aria-label="Close attachment viewer"
            onClick={onClose}
          />
        </div>

        <div className="attachment-viewer-body">
          {isLoading && (
            <div className="text-secondary text-center py-5">
              Loading attachment…
            </div>
          )}

          {!isLoading && error && !blob && (
            <div className="alert alert-danger mb-0">
              {error}
            </div>
          )}

          {!isLoading
            && !error
            && previewKind === 'unsupported' && (
              <div className="text-secondary text-center py-5">
                This file type does not have an in-app preview yet.
                You can still download it safely without leaving the app.
              </div>
            )}

          {!isLoading
            && previewKind === 'image'
            && objectUrl && (
              <img
                className="attachment-preview-image"
                src={objectUrl}
                alt={attachment.original_filename}
              />
            )}

          {!isLoading
            && previewKind === 'audio'
            && objectUrl && (
              <audio
                className="w-100"
                controls
                src={objectUrl}
              />
            )}

          {!isLoading
            && previewKind === 'video'
            && objectUrl && (
              <video
                className="attachment-preview-video"
                controls
                src={objectUrl}
              />
            )}

          {!isLoading
            && previewKind === 'pdf'
            && objectUrl && (
              <iframe
                className="attachment-preview-document"
                src={objectUrl}
                title={attachment.original_filename}
              />
            )}

          {!isLoading
            && previewKind === 'text'
            && textContent !== null && (
              <pre className="attachment-preview-text mb-0">
                {textContent}
              </pre>
            )}
        </div>

        <div className="attachment-viewer-footer">
          {error && blob && (
            <span className="text-danger small me-auto">
              {error}
            </span>
          )}

          <button
            className="btn btn-outline-secondary"
            type="button"
            onClick={onClose}
          >
            Close
          </button>

          <button
            className="btn btn-primary"
            type="button"
            disabled={isDownloading}
            onClick={() => {
              void handleDownload()
            }}
          >
            {isDownloading
              ? 'Downloading…'
              : 'Download'}
          </button>
        </div>
      </div>
    </div>
  )
}


export default AttachmentViewer
