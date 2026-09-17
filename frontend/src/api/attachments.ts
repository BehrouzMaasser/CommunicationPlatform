import {
  apiGetBlob,
} from './client'


export function getAttachmentFile(
  downloadUrl: string,
  signal?: AbortSignal,
): Promise<Blob> {
  return apiGetBlob(
    downloadUrl,
    signal,
  )
}
