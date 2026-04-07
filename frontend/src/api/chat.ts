import type { ChatRequest, ChatStreamEvent, ChartSpec } from './types'

export interface StreamChatOptions {
  signal?: AbortSignal
  userName?: string
}

function isChatStreamEvent(payload: unknown): payload is ChatStreamEvent {
  if (typeof payload !== 'object' || payload === null) return false
  const event = payload as { type?: string; token?: unknown; chart?: unknown; message?: unknown }
  if (event.type === 'token') return typeof event.token === 'string'
  if (event.type === 'chart_spec') return !!event.chart && typeof event.chart === 'object'
  if (event.type === 'done') return true
  if (event.type === 'error') return typeof event.message === 'string'
  return false
}

/** Parse completed SSE lines and yield typed chat stream events. */
function* parseSSELines(lines: string[]): Generator<ChatStreamEvent> {
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    const raw = line.slice(6).trim()
    try {
      const payload = JSON.parse(raw) as unknown
      if (!isChatStreamEvent(payload)) continue

      if (payload.type === 'chart_spec') {
        const chart = payload.chart as ChartSpec
        if (!chart || typeof chart !== 'object') continue
      }

      yield payload
      if (payload.type === 'done') return
    } catch {
      // skip malformed frames
    }
  }
}

/** Stream a chat completion as typed token/chart/error/done events. */
export async function* streamChat(
  req: ChatRequest,
  options?: StreamChatOptions,
): AsyncGenerator<ChatStreamEvent> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options?.userName) headers['X-User-Name'] = options.userName

  let resp: Response
  try {
    resp = await fetch('./api/chat', {
      method: 'POST',
      headers,
      body: JSON.stringify(req),
      signal: options?.signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw err
  }

  if (!resp.ok) throw new Error(`Chat API: HTTP ${resp.status}`)
  if (!resp.body) throw new Error('Chat API: no response body')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n')
      buffer = parts[parts.length - 1] ?? ''
      for (const event of parseSSELines(parts.slice(0, -1))) {
        yield event
        if (event.type === 'done') return
      }
    }
    if (buffer.trim()) {
      for (const event of parseSSELines([buffer])) {
        yield event
        if (event.type === 'done') return
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw err
  } finally {
    reader.cancel().catch(() => {})
  }
}
