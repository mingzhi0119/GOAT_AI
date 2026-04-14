import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
import { parseChatStreamEvent } from './runtimeSchemas'
import type { ChatRequest, ChatStreamEvent } from './types'
import { buildApiUrl } from './urls'

export interface StreamChatOptions {
  signal?: AbortSignal
  userName?: string
}

/** Parse completed SSE lines and yield typed chat stream events. */
function* parseSSELines(lines: string[]): Generator<ChatStreamEvent> {
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    const raw = line.slice(6).trim()
    try {
      const payload = JSON.parse(raw) as unknown
      const event = parseChatStreamEvent(payload)
      yield event
      if (event.type === 'done') return
    } catch {
      // skip malformed frames
    }
  }
}

/** Stream a chat completion as typed token/chart/artifact/error/done events. */
export async function* streamChat(
  req: ChatRequest,
  options?: StreamChatOptions,
): AsyncGenerator<ChatStreamEvent> {
  const headers = buildApiHeaders({ 'Content-Type': 'application/json' })
  if (options?.userName) headers['X-User-Name'] = options.userName

  let resp: Response
  try {
    resp = await fetch(buildApiUrl('/chat'), {
      method: 'POST',
      headers,
      body: JSON.stringify(req),
      signal: options?.signal,
    })
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw err
  }

  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Chat API'))
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
