/** POST /api/media/uploads — vision image attachments. */

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
  const resp = await fetch('./api/media/uploads', { method: 'POST', body })
  if (!resp.ok) {
    throw new Error(`Media upload API: HTTP ${resp.status}`)
  }
  return (await resp.json()) as MediaUploadResponse
}
