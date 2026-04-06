import type { ChatRequest, ChatStreamEvent, ChartSpec } from './types'

export interface StreamChatOptions {
  signal?: AbortSignal
  userName?: string
}

/** Parse completed SSE lines and yield decoded token strings or chart_spec objects. */
function* parseSSELines(lines: string[]): Generator<ChatStreamEvent> {
  for (const line of lines) {
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
        (payload as { type?: string }).type === 'chart_spec'
      ) {
        const chart = (payload as { type: string; chart: ChartSpec }).chart
        if (chart && typeof chart === 'object') yield chart
      }
    } catch {
      // skip malformed frames
    }
  }
}

/** Stream a chat completion as token strings and optional chart_spec events. */
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
      }
    }
    if (buffer.trim()) {
      for (const event of parseSSELines([buffer])) {
        yield event
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw err
  } finally {
    reader.cancel().catch(() => {})
  }
}
