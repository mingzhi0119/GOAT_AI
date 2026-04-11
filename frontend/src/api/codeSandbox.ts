import type {
  CodeSandboxExecRequest,
  CodeSandboxExecutionEventsResponse,
  CodeSandboxLogStreamEvent,
  CodeSandboxExecutionResponse,
} from './types'

function extractErrorDetail(payload: unknown): string | null {
  if (typeof payload !== 'object' || payload === null) return null
  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return 'Request validation failed.'
  return null
}

async function parseErrorResponse(resp: Response): Promise<string> {
  try {
    const payload = (await resp.json()) as unknown
    return extractErrorDetail(payload) ?? `Code sandbox API: HTTP ${resp.status}`
  } catch {
    return `Code sandbox API: HTTP ${resp.status}`
  }
}

export async function executeCodeSandbox(
  request: CodeSandboxExecRequest,
): Promise<CodeSandboxExecutionResponse> {
  const resp = await fetch('./api/code-sandbox/exec', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!resp.ok) throw new Error(await parseErrorResponse(resp))
  return (await resp.json()) as CodeSandboxExecutionResponse
}

export async function fetchCodeSandboxExecution(
  executionId: string,
): Promise<CodeSandboxExecutionResponse> {
  const resp = await fetch(`./api/code-sandbox/executions/${executionId}`)
  if (!resp.ok) throw new Error(await parseErrorResponse(resp))
  return (await resp.json()) as CodeSandboxExecutionResponse
}

export async function fetchCodeSandboxExecutionEvents(
  executionId: string,
): Promise<CodeSandboxExecutionEventsResponse> {
  const resp = await fetch(`./api/code-sandbox/executions/${executionId}/events`)
  if (!resp.ok) throw new Error(await parseErrorResponse(resp))
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
  const url = new URL(`./api/code-sandbox/executions/${executionId}/logs`, window.location.href)
  if (options.afterSequence && options.afterSequence > 0) {
    url.searchParams.set('after_seq', String(options.afterSequence))
  }
  const source = new EventSource(url.toString())
  source.onmessage = event => {
    try {
      options.onEvent(JSON.parse(event.data) as CodeSandboxLogStreamEvent)
    } catch {
      // Ignore malformed SSE frames and keep the stream alive.
    }
  }
  source.onerror = () => {
    source.close()
    options.onError?.()
  }
  return () => source.close()
}
