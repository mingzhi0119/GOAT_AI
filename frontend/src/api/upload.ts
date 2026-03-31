/** Stream CSV/XLSX upload analysis as tokens via Server-Sent Events. */
export interface UploadFileContextEvent {
  type: 'file_context'
  filename: string
  prompt: string
}

export type UploadStreamEvent = string | UploadFileContextEvent

/** Stream CSV/XLSX upload analysis events via Server-Sent Events. */
export async function* streamUpload(
  file: File,
  model: string,
): AsyncGenerator<UploadStreamEvent> {
  const form = new FormData()
  form.append('file', file)
  form.append('model', model)

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
        if (typeof payload === 'string') {
          if (payload === '[DONE]') return
          yield payload
          continue
        }
        if (
          typeof payload === 'object' &&
          payload !== null &&
          (payload as { type?: string }).type === 'file_context'
        ) {
          const event = payload as UploadFileContextEvent
          if (typeof event.filename === 'string' && typeof event.prompt === 'string') {
            yield event
          }
        }
      } catch {
        // skip malformed frames
      }
    }
  }
}
