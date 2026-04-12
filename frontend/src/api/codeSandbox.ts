import { buildApiHeaders } from './auth'
import { buildApiErrorMessage } from './errors'
import type {
  CodeSandboxExecRequest,
  CodeSandboxExecutionEventsResponse,
  CodeSandboxLogStreamEvent,
  CodeSandboxExecutionResponse,
} from './types'

function emitParsedEvent(line: string, onEvent: (event: CodeSandboxLogStreamEvent) => void): void {
  if (!line.startsWith('data: ')) return
  try {
    onEvent(JSON.parse(line.slice(6).trim()) as CodeSandboxLogStreamEvent)
  } catch {
    // Ignore malformed SSE frames and keep the stream alive.
  }
}

export async function executeCodeSandbox(
  request: CodeSandboxExecRequest,
): Promise<CodeSandboxExecutionResponse> {
  const resp = await fetch('./api/code-sandbox/exec', {
    method: 'POST',
    headers: buildApiHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(request),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Code sandbox API'))
  return (await resp.json()) as CodeSandboxExecutionResponse
}

export async function fetchCodeSandboxExecution(
  executionId: string,
): Promise<CodeSandboxExecutionResponse> {
  const resp = await fetch(`./api/code-sandbox/executions/${executionId}`, {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Code sandbox API'))
  return (await resp.json()) as CodeSandboxExecutionResponse
}

export async function fetchCodeSandboxExecutionEvents(
  executionId: string,
): Promise<CodeSandboxExecutionEventsResponse> {
  const resp = await fetch(`./api/code-sandbox/executions/${executionId}/events`, {
    headers: buildApiHeaders(),
  })
  if (!resp.ok) throw new Error(await buildApiErrorMessage(resp, 'Code sandbox API'))
  return (await resp.json()) as CodeSandboxExecutionEventsResponse
}

interface CodeSandboxLogStreamOptions {
  afterSequence?: number
  onEvent: (event: CodeSandboxLogStreamEvent) => void
  onError?: () => void
}

export function openCodeSandboxLogStream(
  executionId: string,
  options: CodeSandboxLogStreamOptions,
): () => void {
  const controller = new AbortController()
  const url = new URL(`./api/code-sandbox/executions/${executionId}/logs`, window.location.href)
  if (options.afterSequence && options.afterSequence > 0) {
    url.searchParams.set('after_seq', String(options.afterSequence))
  }

  void (async () => {
    try {
      const resp = await fetch(url.toString(), {
        headers: buildApiHeaders(),
        signal: controller.signal,
      })
      if (!resp.ok) {
        throw new Error(await buildApiErrorMessage(resp, 'Code sandbox log stream'))
      }
      if (!resp.body) {
        throw new Error('Code sandbox log stream: no response body')
      }

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
          for (const line of parts.slice(0, -1)) {
            emitParsedEvent(line, options.onEvent)
          }
        }
        if (buffer.trim()) {
          emitParsedEvent(buffer, options.onEvent)
        }
      } finally {
        reader.cancel().catch(() => {})
      }
    } catch {
      if (!controller.signal.aborted) {
        options.onError?.()
      }
    }
  })()

  return () => controller.abort()
}
