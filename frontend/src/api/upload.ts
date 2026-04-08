/** Stream file-ingestion events from the RAG knowledge upload pipeline. */

export interface UploadKnowledgeReadyEvent {
  type: 'knowledge_ready'
  filename: string
  document_id: string
  ingestion_id: string
  status: string
  retrieval_mode: string
}

export interface UploadErrorEvent {
  type: 'error'
  message: string
}

export interface UploadDoneEvent {
  type: 'done'
}

export type UploadStreamEvent = UploadKnowledgeReadyEvent | UploadErrorEvent | UploadDoneEvent

function isUploadStreamEvent(payload: unknown): payload is UploadStreamEvent {
  if (typeof payload !== 'object' || payload === null) return false
  const event = payload as {
    type?: string
    filename?: unknown
    document_id?: unknown
    ingestion_id?: unknown
    status?: unknown
    retrieval_mode?: unknown
    message?: unknown
  }
  if (event.type === 'knowledge_ready') {
    return (
      typeof event.filename === 'string' &&
      typeof event.document_id === 'string' &&
      typeof event.ingestion_id === 'string' &&
      typeof event.status === 'string' &&
      typeof event.retrieval_mode === 'string'
    )
  }
  if (event.type === 'error') return typeof event.message === 'string'
  if (event.type === 'done') return true
  return false
}

/** Ingest a supported file and yield typed readiness events. */
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
