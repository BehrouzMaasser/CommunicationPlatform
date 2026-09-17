export function downloadBrowserBlob(
  blob: Blob,
  filename: string,
): void {
  const objectUrl =
    URL.createObjectURL(blob)

  const anchor =
    document.createElement('a')

  anchor.href = objectUrl
  anchor.download = filename
  anchor.target = '_blank'
  anchor.rel = 'noopener'
  anchor.style.display = 'none'

  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()

  window.setTimeout(
    () => {
      URL.revokeObjectURL(
        objectUrl,
      )
    },
    1000,
  )
}
