import { extractApiErrorCode, extractApiErrorDetail } from './errors'
import {
  parseBrowserAuthSessionResponse,
  parseGoogleOAuthUrlResponse,
} from './runtimeSchemas'
import type { BrowserAuthSession, GoogleOAuthUrlResponse } from './types'
import { buildApiUrl } from './urls'

export class BrowserAuthApiError extends Error {
  code: string | null
  status: number

  constructor(message: string, options: { code: string | null; status: number }) {
    super(message)
    this.name = 'BrowserAuthApiError'
    this.code = options.code
    this.status = options.status
  }
}

async function parseErrorResponse(
  resp: Response,
  fallbackMessage: string,
): Promise<BrowserAuthApiError> {
  try {
    const payload = await resp.json()
    return new BrowserAuthApiError(
      extractApiErrorDetail(payload) ?? fallbackMessage,
      {
        code: extractApiErrorCode(payload),
        status: resp.status,
      },
    )
  } catch {
    return new BrowserAuthApiError(fallbackMessage, {
      code: null,
      status: resp.status,
    })
  }
}

async function readSessionResponse(
  resp: Response,
  fallbackMessage: string,
): Promise<BrowserAuthSession> {
  if (!resp.ok) {
    throw await parseErrorResponse(resp, fallbackMessage)
  }
  return parseBrowserAuthSessionResponse(await resp.json())
}

async function readGoogleUrlResponse(
  resp: Response,
  fallbackMessage: string,
): Promise<GoogleOAuthUrlResponse> {
  if (!resp.ok) {
    throw await parseErrorResponse(resp, fallbackMessage)
  }
  return parseGoogleOAuthUrlResponse(await resp.json())
}

export async function fetchBrowserAuthSession(): Promise<BrowserAuthSession> {
  const resp = await fetch(buildApiUrl('/auth/session'), {
    credentials: 'same-origin',
  })
  return readSessionResponse(resp, 'Failed to load browser session')
}

export async function loginSharedBrowserAuth(password: string): Promise<BrowserAuthSession> {
  const resp = await fetch(buildApiUrl('/auth/login'), {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  return readSessionResponse(resp, 'Shared password login failed')
}

export async function loginAccountBrowserAuth(
  email: string,
  password: string,
): Promise<BrowserAuthSession> {
  const resp = await fetch(buildApiUrl('/auth/account/login'), {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return readSessionResponse(resp, 'Account login failed')
}

export async function fetchGoogleOAuthUrl(): Promise<GoogleOAuthUrlResponse> {
  const resp = await fetch(buildApiUrl('/auth/account/google/url'), {
    credentials: 'same-origin',
  })
  return readGoogleUrlResponse(resp, 'Failed to start Google login')
}

export async function completeGoogleBrowserAuth(
  code: string,
  state: string,
): Promise<BrowserAuthSession> {
  const resp = await fetch(buildApiUrl('/auth/account/google'), {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, state }),
  })
  return readSessionResponse(resp, 'Google login failed')
}

export async function logoutBrowserAuth(): Promise<void> {
  const resp = await fetch(buildApiUrl('/auth/logout'), {
    method: 'POST',
    credentials: 'same-origin',
  })
  if (!resp.ok) {
    throw await parseErrorResponse(resp, 'Logout failed')
  }
}
