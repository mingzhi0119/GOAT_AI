import { buildApiErrorMessage } from './errors'
import { parseBrowserAuthSessionResponse } from './runtimeSchemas'
import type { BrowserAuthSession } from './types'
import { buildApiUrl } from './urls'

export async function fetchBrowserAuthSession(): Promise<BrowserAuthSession> {
  const resp = await fetch(buildApiUrl('/auth/session'), {
    credentials: 'same-origin',
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Browser auth session API'))
  }
  return parseBrowserAuthSessionResponse(await resp.json())
}

export async function loginBrowserAuth(password: string): Promise<BrowserAuthSession> {
  const resp = await fetch(buildApiUrl('/auth/login'), {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Shared access login API'))
  }
  return parseBrowserAuthSessionResponse(await resp.json())
}

export async function logoutBrowserAuth(): Promise<void> {
  const resp = await fetch(buildApiUrl('/auth/logout'), {
    method: 'POST',
    credentials: 'same-origin',
  })
  if (!resp.ok) {
    throw new Error(await buildApiErrorMessage(resp, 'Shared access logout API'))
  }
}
