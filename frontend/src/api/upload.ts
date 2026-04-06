/** Stream CSV/XLSX upload parse events via Server-Sent Events.
 *
 * The backend now only parses the file and returns structured metadata
 * (file_context + chart_spec). No LLM inference is triggered on upload;
 * the model answers when the user sends their first follow-up message.
 */
import type { ChartSpec } from './types'

export interface UploadFileContextEvent {
  type: 'file_context'
  filename: string
  prompt: string
}

export interface UploadChartSpecEvent {
  type: 'chart_spec'
  chart: ChartSpec
}

export type UploadStreamEvent = string | UploadFileContextEvent | UploadChartSpecEvent

/** Parse a CSV/XLSX file and yield structured metadata events (no LLM call). */
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
          continue
        }
        if (
          typeof payload === 'object' &&
          payload !== null &&
          (payload as { type?: string }).type === 'chart_spec'
        ) {
          const event = payload as UploadChartSpecEvent
          if (event.chart && typeof event.chart === 'object') {
            yield event
          }
        }
      } catch {
        // skip malformed frames
      }
    }
  }
}
