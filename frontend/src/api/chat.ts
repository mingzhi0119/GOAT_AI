import { buildApiErrorMessage } from './errors'
import { fetchApi } from './http'
import { parseChatStreamEvent } from './runtimeSchemas'
import type { ChatRequest, ChatStreamEvent } from './types'

export interface StreamChatOptions {
  signal?: AbortSignal
  userName?: string
}

const FIRST_EVENT_TIMEOUT_MS = 15_000

function readWithTimeout<T>(promise: Promise<T>, timeoutMs: number, errorMessage: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(errorMessage)), timeoutMs)
    promise.then(
      value => {
        window.clearTimeout(timer)
        resolve(value)
      },
      error => {
        window.clearTimeout(timer)
        reject(error)
      },
    )
  })
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
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (options?.userName) headers['X-User-Name'] = options.userName

  let resp: Response
  try {
    resp = await fetchApi('/chat', {
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
  let sawStreamEvent = false

  try {
    while (true) {
      const { done, value } = sawStreamEvent
        ? await reader.read()
        : await readWithTimeout(
            reader.read(),
            FIRST_EVENT_TIMEOUT_MS,
            'Chat API timed out before streaming any output',
          )
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n')
      buffer = parts[parts.length - 1] ?? ''
      for (const event of parseSSELines(parts.slice(0, -1))) {
        sawStreamEvent = true
        yield event
        if (event.type === 'done') return
      }
    }
    if (buffer.trim()) {
      for (const event of parseSSELines([buffer])) {
        sawStreamEvent = true
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
