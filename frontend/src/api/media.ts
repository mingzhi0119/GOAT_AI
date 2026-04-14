import { buildApiErrorMessage } from './errors'
import { fetchApi } from './http'
import { parseMediaUploadResponse } from './runtimeSchemas'

/** POST /api/media/uploads - vision image attachments. */
export interface MediaUploadResponse {
  attachment_id: string
  filename: string
  mime_type: string
  byte_size: number
  width_px: number | null
  height_px: number | null
}

export async function uploadMediaImage(file: File): Promise<MediaUploadResponse> {
  const body = new FormData()
  body.append('file', file)
  const resp = await fetchApi('/media/uploads', {
    method: 'POST',
    body,
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Media upload API'))
  }
  return parseMediaUploadResponse(await resp.json())
}
