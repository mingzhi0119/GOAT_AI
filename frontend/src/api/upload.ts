import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
import { parseUploadStreamEvent } from './runtimeSchemas'
/** Stream file-ingestion events from the RAG knowledge upload pipeline. */

export interface UploadFilePromptEvent {
  type: 'file_prompt'
  filename: string
  suffix_prompt: string
}

export interface UploadKnowledgeReadyEvent {
  type: 'knowledge_ready'
  filename: string
  suffix_prompt: string
  document_id: string
  ingestion_id: string
  status: string
  retrieval_mode: string
  template_prompt: string
}

export interface UploadErrorEvent {
  type: 'error'
  message: string
}

export interface UploadDoneEvent {
  type: 'done'
}

export type UploadStreamEvent =
  | UploadFilePromptEvent
  | UploadKnowledgeReadyEvent
  | UploadErrorEvent
  | UploadDoneEvent

/** Ingest a supported file and yield typed readiness events. */
export async function* streamUpload(file: File): AsyncGenerator<UploadStreamEvent> {
  const form = new FormData()
  form.append('file', file)

  const resp = await fetch('./api/upload', {
    method: 'POST',
    headers: buildApiHeaders(),
    body: form,
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Upload API'))
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
        const event = parseUploadStreamEvent(payload)
        yield event
        if (event.type === 'done') return
      } catch {
        // skip malformed frames
      }
    }
  }
}
