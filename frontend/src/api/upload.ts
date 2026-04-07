/** Stream CSV/XLSX upload parse events via Server-Sent Events.
 *
 * The backend returns typed SSE objects. Uploading a file produces
 * `file_context`, optional `error`, and terminal `done` events.
 */

export interface UploadFileContextEvent {
  type: 'file_context'
  filename: string
  prompt: string
}

export interface UploadErrorEvent {
  type: 'error'
  message: string
}

export interface UploadDoneEvent {
  type: 'done'
}

export type UploadStreamEvent = UploadFileContextEvent | UploadErrorEvent | UploadDoneEvent

function isUploadStreamEvent(payload: unknown): payload is UploadStreamEvent {
  if (typeof payload !== 'object' || payload === null) return false
  const event = payload as { type?: string; filename?: unknown; prompt?: unknown; message?: unknown }
  if (event.type === 'file_context') {
    return typeof event.filename === 'string' && typeof event.prompt === 'string'
  }
  if (event.type === 'error') return typeof event.message === 'string'
  if (event.type === 'done') return true
  return false
}

/** Parse a CSV/XLSX file and yield typed metadata events. */
export async function* streamUpload(file: File): AsyncGenerator<UploadStreamEvent> {
  const form = new FormData()
  form.append('file', file)

  const resp = await fetch('./api/upload', { method: 'POST', body: form })
  if (!resp.ok) throw new Error(`Upload API: HTTP ${resp.status}`)
  if (!resp.body) throw new Error('Upload API: no response body')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n')
    buffer = parts[parts.length - 1] ?? ''
    for (const line of parts.slice(0, -1)) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      try {
        const payload = JSON.parse(raw) as unknown
        if (!isUploadStreamEvent(payload)) continue
        yield payload
        if (payload.type === 'done') return
      } catch {
        // skip malformed frames
      }
    }
  }
}
