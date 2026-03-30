import type { ChatRequest } from './types'

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
export async function* streamChat(req: ChatRequest): AsyncGenerator<string> {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!resp.ok) throw new Error(`Chat API: HTTP ${resp.status}`)
  if (!resp.body) throw new Error('Chat API: no response body')

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

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
  // flush any remaining data
  if (buffer.trim()) {
    for (const token of parseSSELines([buffer])) {
      yield token
    }
  }
}
