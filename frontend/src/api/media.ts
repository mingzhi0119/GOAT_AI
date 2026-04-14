import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
import { parseMediaUploadResponse } from './runtimeSchemas'
import { buildApiUrl } from './urls'

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
  const resp = await fetch(buildApiUrl('/media/uploads'), {
    method: 'POST',
    headers: buildApiHeaders(),
    body,
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Media upload API'))
  }
  return parseMediaUploadResponse(await resp.json())
}
