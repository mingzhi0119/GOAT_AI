import { buildApiHeaders } from './auth'
import { buildApiUrl } from './urls'

function normalizeHeaders(headers?: HeadersInit): Record<string, string> {
  if (!headers) return {}
  return Object.fromEntries(new Headers(headers).entries())
}

export async function fetchApi(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(buildApiUrl(path), {
    ...init,
    credentials: 'same-origin',
    headers: buildApiHeaders(normalizeHeaders(init.headers)),
  })
}
