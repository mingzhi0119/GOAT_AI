import type { ChatRequest } from './types'

export interface StreamChatOptions {
  signal?: AbortSignal
  userName?: string
}

/** Parse completed SSE lines and yield decoded token strings. */
function* parseSSELines(lines: string[]): Generator<string> {
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue
    const raw = line.slice(6).trim()
    try {
      const token = JSON.parse(raw) as string
      if (token === '[DONE]') return
      yield token
    } catch {
      // skip malformed frames
    }
  }
}

/** Stream a chat completion as tokens via Server-Sent Events. */
export async function* streamChat(
  req: ChatRequest,
  options?: StreamChatOptions,
): AsyncGenerator<string> {
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
      for (const token of parseSSELines(parts.slice(0, -1))) {
        yield token
      }
    }
    if (buffer.trim()) {
      for (const token of parseSSELines([buffer])) {
        yield token
      }
    }
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw err
  } finally {
    reader.cancel().catch(() => {})
  }
}
