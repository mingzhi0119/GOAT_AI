import { buildApiHeaders } from './auth'
import { extractApiErrorCode } from './errors'
import { buildApiUrl } from './urls'

export const API_AUTH_REQUIRED_EVENT = 'goat:auth-required'

function normalizeHeaders(headers?: HeadersInit): Record<string, string> {
  if (!headers) return {}
  return Object.fromEntries(new Headers(headers).entries())
}

function dispatchAuthRequiredEvent(): void {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(API_AUTH_REQUIRED_EVENT))
}

async function maybeDispatchAuthRequired(resp: Response): Promise<void> {
  if (resp.status !== 401) return
  try {
    const payload: unknown = await resp.json()
    const code = extractApiErrorCode(payload)
    if (code === null || code === 'AUTH_LOGIN_REQUIRED' || code === 'AUTH_INVALID_API_KEY') {
      dispatchAuthRequiredEvent()
    }
  } catch {
    dispatchAuthRequiredEvent()
  }
}

export async function fetchApi(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    credentials: 'same-origin',
    headers: buildApiHeaders(normalizeHeaders(init.headers)),
  })
  if (typeof response.clone === 'function') {
    void maybeDispatchAuthRequired(response.clone())
  } else if (response.status === 401) {
    dispatchAuthRequiredEvent()
  }
  return response
}
