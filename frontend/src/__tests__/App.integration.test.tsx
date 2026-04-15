/* @vitest-environment jsdom */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../utils/browserNavigation', () => ({
  navigateToExternalUrl: vi.fn(),
}))

vi.mock('@tauri-apps/api/core', () => ({
  invoke: vi.fn(),
}))

import App from '../App'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { BrowserAuthApiError } from '../api/browserAuth'
import { buildApiUrl } from '../api/urls'
import { AppearanceProvider } from '../hooks/useAppearance'
import { invoke } from '@tauri-apps/api/core'
import { navigateToExternalUrl } from '../utils/browserNavigation'

const AUTH_SESSION_URL = buildApiUrl('/auth/session')
const AUTH_LOGIN_URL = buildApiUrl('/auth/login')
const AUTH_ACCOUNT_LOGIN_URL = buildApiUrl('/auth/account/login')
const AUTH_GOOGLE_URL_URL = buildApiUrl('/auth/account/google/url')
const AUTH_GOOGLE_URL = buildApiUrl('/auth/account/google')
const AUTH_LOGOUT_URL = buildApiUrl('/auth/logout')
const MODELS_URL = buildApiUrl('/models')
const MODEL_CAPABILITIES_URL_PREFIX = buildApiUrl('/models/capabilities')
const HISTORY_URL = buildApiUrl('/history')
const SYSTEM_FEATURES_URL = buildApiUrl('/system/features')
const SYSTEM_GPU_URL = buildApiUrl('/system/gpu')
const SYSTEM_INFERENCE_URL = buildApiUrl('/system/inference')
const CHAT_URL = buildApiUrl('/chat')

function matchesRequestUrl(actual: string, expected: string): boolean {
  if (actual === expected) return true
  try {
    return new URL(actual).pathname === new URL(expected).pathname
  } catch {
    return false
  }
}

interface TestBrowserAuthUser {
  id: string
  email: string
  display_name: string
  provider: 'local' | 'google'
}

interface TestBrowserAuthSession {
  auth_required: boolean
  authenticated: boolean
  expires_at: string | null
  available_login_methods: ('shared_password' | 'account_password' | 'google')[]
  active_login_method: 'shared_password' | 'account_password' | 'google' | null
  user: TestBrowserAuthUser | null
}

function buildBrowserAuthSession(
  overrides: Partial<TestBrowserAuthSession> = {},
): TestBrowserAuthSession {
  return {
    auth_required: false,
    authenticated: false,
    expires_at: null,
    available_login_methods: [],
    active_login_method: null,
    user: null,
    ...overrides,
  }
}

function buildJsonResponse(payload: unknown, ok = true) {
  return {
    ok,
    json: async () => payload,
  }
}

function buildStreamResponse(chunks: string[]) {
  const encoder = new TextEncoder()
  return {
    ok: true,
    body: new ReadableStream<Uint8Array>({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk))
        }
        controller.close()
      },
    }),
  }
}

function buildFetchMock(options?: {
  authSession?: TestBrowserAuthSession
  authSessionSequence?: (TestBrowserAuthSession | Error)[]
  sharedLoginSession?: TestBrowserAuthSession
  accountLoginSession?: TestBrowserAuthSession
  googleLoginSession?: TestBrowserAuthSession
  googleAuthorizationUrl?: string
}) {
  const authSession = options?.authSession ?? buildBrowserAuthSession()
  const authSessionSequence = options?.authSessionSequence ?? [authSession]
  const sharedLoginSession =
    options?.sharedLoginSession ??
    buildBrowserAuthSession({
      auth_required: true,
      authenticated: true,
      expires_at: '2026-05-13T20:00:00Z',
      available_login_methods: ['shared_password'],
      active_login_method: 'shared_password',
    })
  const accountLoginSession =
    options?.accountLoginSession ??
    buildBrowserAuthSession({
      auth_required: true,
      authenticated: true,
      expires_at: '2026-05-13T20:00:00Z',
      available_login_methods: ['account_password', 'google'],
      active_login_method: 'account_password',
      user: {
        id: 'user-1',
        email: 'user@example.com',
        display_name: 'User Example',
        provider: 'local',
      },
    })
  const googleLoginSession =
    options?.googleLoginSession ??
    buildBrowserAuthSession({
      auth_required: true,
      authenticated: true,
      expires_at: '2026-05-13T20:00:00Z',
      available_login_methods: ['account_password', 'google'],
      active_login_method: 'google',
      user: {
        id: 'user-2',
        email: 'google@example.com',
        display_name: 'Google User',
        provider: 'google',
      },
    })
  const googleAuthorizationUrl =
    options?.googleAuthorizationUrl ??
    'https://accounts.google.com/o/oauth2/v2/auth?state=test-google-state'
  let authSessionCallCount = 0

  return vi.fn().mockImplementation((input: string, init?: RequestInit) => {
    if (matchesRequestUrl(input, AUTH_SESSION_URL)) {
      const nextAuthSession =
        authSessionSequence[
          Math.min(authSessionCallCount, authSessionSequence.length - 1)
        ]
      authSessionCallCount += 1
      if (nextAuthSession instanceof Error) {
        return Promise.reject(nextAuthSession)
      }
      return Promise.resolve(buildJsonResponse(nextAuthSession))
    }
    if (matchesRequestUrl(input, AUTH_LOGIN_URL)) {
      return Promise.resolve(buildJsonResponse(sharedLoginSession))
    }
    if (matchesRequestUrl(input, AUTH_ACCOUNT_LOGIN_URL)) {
      return Promise.resolve(buildJsonResponse(accountLoginSession))
    }
    if (matchesRequestUrl(input, AUTH_GOOGLE_URL_URL)) {
      return Promise.resolve(
        buildJsonResponse({
          authorization_url: googleAuthorizationUrl,
          state_expires_at: '2026-05-13T20:00:00Z',
        }),
      )
    }
    if (matchesRequestUrl(input, AUTH_GOOGLE_URL)) {
      return Promise.resolve(buildJsonResponse(googleLoginSession))
    }
    if (matchesRequestUrl(input, AUTH_LOGOUT_URL)) {
      return Promise.resolve({ ok: true })
    }
    if (matchesRequestUrl(input, MODELS_URL)) {
      return Promise.resolve(buildJsonResponse({ models: ['gemma4:26b'] }))
    }
    if (
      input.startsWith(MODEL_CAPABILITIES_URL_PREFIX) ||
      new URL(input).pathname === new URL(MODEL_CAPABILITIES_URL_PREFIX).pathname
    ) {
      return Promise.resolve(
        buildJsonResponse({
          model: 'gemma4:26b',
          capabilities: ['thinking'],
          supports_tool_calling: false,
          supports_chart_tools: false,
          supports_vision: false,
          supports_thinking: true,
          context_length: 8192,
        }),
      )
    }
    if (matchesRequestUrl(input, HISTORY_URL)) {
      if (init?.method === 'DELETE') {
        return Promise.resolve(buildJsonResponse({}))
      }
      return Promise.resolve(buildJsonResponse({ sessions: [] }))
    }
    if (matchesRequestUrl(input, SYSTEM_FEATURES_URL)) {
      return Promise.resolve(
        buildJsonResponse({
          code_sandbox: {
            policy_allowed: true,
            allowed_by_config: false,
            available_on_host: false,
            effective_enabled: false,
            provider_name: 'docker',
            isolation_level: 'container',
            network_policy_enforced: true,
            deny_reason: null,
          },
          workbench: {
            agent_tasks: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            plan_mode: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            browse: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            deep_research: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            artifact_workspace: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            artifact_exports: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            project_memory: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
            connectors: {
              allowed_by_config: false,
              available_on_host: false,
              effective_enabled: false,
              deny_reason: null,
            },
          },
        }),
      )
    }
    if (matchesRequestUrl(input, SYSTEM_GPU_URL)) {
      return Promise.resolve(
        buildJsonResponse({
          available: true,
          active: false,
          message: 'idle',
          name: 'A100',
          uuid: 'GPU-1',
          utilization_gpu: 0,
          memory_used_mb: 0,
          memory_total_mb: 40960,
          temperature_c: 35,
          power_draw_w: 120,
        }),
      )
    }
    if (matchesRequestUrl(input, SYSTEM_INFERENCE_URL)) {
      return Promise.resolve(
        buildJsonResponse({
          chat_avg_ms: 10,
          chat_sample_count: 1,
          chat_p50_ms: 10,
          chat_p95_ms: 10,
          first_token_avg_ms: 5,
          first_token_sample_count: 1,
          first_token_p50_ms: 5,
          first_token_p95_ms: 5,
          model_buckets: {},
        }),
      )
    }
    if (matchesRequestUrl(input, CHAT_URL)) {
      return Promise.resolve(
        buildStreamResponse([
          'data: {"type":"token","token":"Hello back"}\n\n',
          'data: {"type":"done"}\n\n',
        ]),
      )
    }

    throw new Error(`Unexpected fetch request: ${input}`)
  })
}

function findCall(
  mockedFetch: ReturnType<typeof buildFetchMock>,
  url: string,
  predicate?: (init: RequestInit | undefined) => boolean,
) {
  return mockedFetch.mock.calls.find(([calledUrl, init]) => {
    if (!matchesRequestUrl(calledUrl as string, url)) return false
    return predicate ? predicate(init as RequestInit | undefined) : true
  })
}

async function waitForStartupFetches(mockedFetch: ReturnType<typeof buildFetchMock>) {
  await waitFor(() => {
    expect(findCall(mockedFetch, MODELS_URL)).toBeTruthy()
    expect(findCall(mockedFetch, HISTORY_URL)).toBeTruthy()
    expect(findCall(mockedFetch, SYSTEM_FEATURES_URL)).toBeTruthy()
    expect(findCall(mockedFetch, SYSTEM_GPU_URL)).toBeTruthy()
    expect(findCall(mockedFetch, SYSTEM_INFERENCE_URL)).toBeTruthy()
  })
}

function renderApp() {
  return render(
    <AppearanceProvider>
      <App />
    </AppearanceProvider>,
  )
}

describe('App browser access integration', () => {
  afterEach(() => {
    window.history.replaceState({}, '', '/')
    localStorage.clear()
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('blocks startup API calls behind shared-access login and clears private state', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'owner-42')
    localStorage.setItem('goat-ai-username', 'Alice')
    localStorage.setItem('goat-ai-system-instruction', 'Use bullets')
    localStorage.setItem('goat-ai-file-context', JSON.stringify([{ filename: 'brief.md' }]))
    localStorage.setItem('goat-ai-messages', JSON.stringify([{ id: 'm1', role: 'assistant' }]))
    localStorage.setItem('goat-ai-session-id', 'sess-1')
    const mockedFetch = buildFetchMock({
      authSession: buildBrowserAuthSession({
        auth_required: true,
        available_login_methods: ['shared_password', 'account_password', 'google'],
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()

    await screen.findByLabelText('Shared password')
    expect(screen.getByRole('button', { name: /enter goat/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /shared password/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /account login/i })).toBeInTheDocument()
    expect(mockedFetch).toHaveBeenCalledTimes(1)
    expect(findCall(mockedFetch, AUTH_SESSION_URL)?.[1]).toMatchObject({
      credentials: 'same-origin',
    })
    expect(findCall(mockedFetch, MODELS_URL)).toBeFalsy()
    expect(findCall(mockedFetch, HISTORY_URL)).toBeFalsy()
    expect(findCall(mockedFetch, SYSTEM_FEATURES_URL)).toBeFalsy()
    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem('goat-ai-username')).toBeNull()
    expect(localStorage.getItem('goat-ai-system-instruction')).toBeNull()
    expect(localStorage.getItem('goat-ai-file-context')).toBeNull()
    expect(localStorage.getItem('goat-ai-messages')).toBeNull()
    expect(localStorage.getItem('goat-ai-session-id')).toBeNull()
  })

  it('uses persisted protected-access headers for startup API calls outside shared mode', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'owner-42')
    const mockedFetch = buildFetchMock()
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await waitForStartupFetches(mockedFetch)

    expect(findCall(mockedFetch, AUTH_SESSION_URL)?.[1]).toMatchObject({
      credentials: 'same-origin',
    })
    for (const url of [
      MODELS_URL,
      HISTORY_URL,
      SYSTEM_FEATURES_URL,
      SYSTEM_GPU_URL,
      SYSTEM_INFERENCE_URL,
    ]) {
      const call = findCall(mockedFetch, url)
      expect(call?.[1]).toMatchObject({
        credentials: 'same-origin',
        headers: {
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'owner-42',
        },
      })
    }
  })

  it('waits for login before mounting the shell and surfaces logout in settings', async () => {
    const mockedFetch = buildFetchMock({
      authSession: buildBrowserAuthSession({
        auth_required: true,
        available_login_methods: ['shared_password'],
      }),
      sharedLoginSession: buildBrowserAuthSession({
        auth_required: true,
        authenticated: true,
        expires_at: '2026-05-13T20:00:00Z',
        available_login_methods: ['shared_password'],
        active_login_method: 'shared_password',
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await screen.findByLabelText('Shared password')
    expect(findCall(mockedFetch, MODELS_URL)).toBeFalsy()

    fireEvent.change(screen.getByLabelText('Shared password'), {
      target: { value: 'goat-shared-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /enter goat/i }))

    await waitFor(() => {
      expect(findCall(mockedFetch, AUTH_LOGIN_URL)).toBeTruthy()
    })
    await waitForStartupFetches(mockedFetch)

    localStorage.setItem('goat-ai-messages', JSON.stringify([{ id: 'm1', role: 'assistant' }]))
    localStorage.setItem('goat-ai-session-id', 'sess-1')

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    expect(screen.getByText('Session')).toBeInTheDocument()
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Owner ID')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /logout/i }))

    await screen.findByLabelText('Shared password')
    expect(findCall(mockedFetch, AUTH_LOGOUT_URL)?.[1]).toMatchObject({
      credentials: 'same-origin',
      method: 'POST',
    })
    expect(localStorage.getItem('goat-ai-messages')).toBeNull()
    expect(localStorage.getItem('goat-ai-session-id')).toBeNull()
  })

  it('supports account password login from the unified browser gate', async () => {
    const mockedFetch = buildFetchMock({
      authSession: buildBrowserAuthSession({
        auth_required: true,
        available_login_methods: ['shared_password', 'account_password', 'google'],
      }),
      accountLoginSession: buildBrowserAuthSession({
        auth_required: true,
        authenticated: true,
        expires_at: '2026-05-13T20:00:00Z',
        available_login_methods: ['shared_password', 'account_password', 'google'],
        active_login_method: 'account_password',
        user: {
          id: 'user-1',
          email: 'user@example.com',
          display_name: 'User Example',
          provider: 'local',
        },
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await screen.findByRole('tab', { name: /account login/i })
    fireEvent.click(screen.getByRole('tab', { name: /account login/i }))

    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'user@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'account-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^sign in$/i }))

    await waitFor(() => {
      expect(findCall(mockedFetch, AUTH_ACCOUNT_LOGIN_URL)).toBeTruthy()
    })
    await waitForStartupFetches(mockedFetch)

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    expect(screen.getByText('User Example (user@example.com)')).toBeInTheDocument()
    expect(screen.queryByLabelText('API key')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Owner ID')).not.toBeInTheDocument()
  })

  it('retries desktop auth bootstrap until the bundled backend is reachable', async () => {
    vi.spyOn(document, 'baseURI', 'get').mockReturnValue('https://asset.localhost/index.html')
    const mockedFetch = buildFetchMock({
      authSessionSequence: [new TypeError('Failed to fetch'), buildBrowserAuthSession()],
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await waitForStartupFetches(mockedFetch)

    expect(screen.queryByText('GOAT startup')).not.toBeInTheDocument()
    expect(screen.queryByText(/Unable to load this deployment right now/i)).not.toBeInTheDocument()
    await waitFor(() => {
      expect(vi.mocked(invoke)).toHaveBeenCalledWith('report_frontend_bootstrap_status', {
        status: 'ready',
      })
    })
    expect(
      vi
        .mocked(invoke)
        .mock.calls.filter(([command]) => command === 'report_frontend_bootstrap_status')
        .map(([, payload]) => payload),
    ).toEqual([{ status: 'ready' }])
  })

  it('reports failed desktop bootstrap only for terminal startup errors', async () => {
    vi.spyOn(document, 'baseURI', 'get').mockReturnValue('https://asset.localhost/index.html')
    const mockedFetch = buildFetchMock({
      authSessionSequence: [
        new BrowserAuthApiError('Desktop startup issue.', {
          code: null,
          status: 503,
        }),
      ],
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()

    await screen.findByText('Desktop startup issue.')
    await waitFor(() => {
      expect(vi.mocked(invoke)).toHaveBeenCalledWith('report_frontend_bootstrap_status', {
        status: 'failed',
      })
    })
    expect(screen.getByText('GOAT AI desktop')).toBeInTheDocument()
  })

  it('starts Google login from the unified browser gate', async () => {
    const mockedFetch = buildFetchMock({
      authSession: buildBrowserAuthSession({
        auth_required: true,
        available_login_methods: ['account_password', 'google'],
      }),
      googleAuthorizationUrl:
        'https://accounts.google.com/o/oauth2/v2/auth?state=google-state-123',
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await screen.findByRole('button', { name: /continue with google/i })
    fireEvent.click(screen.getByRole('button', { name: /continue with google/i }))

    await waitFor(() => {
      expect(findCall(mockedFetch, AUTH_GOOGLE_URL_URL)).toBeTruthy()
    })
    expect(navigateToExternalUrl).toHaveBeenCalledWith(
      'https://accounts.google.com/o/oauth2/v2/auth?state=google-state-123',
    )
  })

  it('completes the Google OAuth callback before mounting the shell', async () => {
    window.history.pushState({}, '', '/?code=oauth-code&state=oauth-state&scope=email')
    const mockedFetch = buildFetchMock({
      googleLoginSession: buildBrowserAuthSession({
        auth_required: true,
        authenticated: true,
        expires_at: '2026-05-13T20:00:00Z',
        available_login_methods: ['account_password', 'google'],
        active_login_method: 'google',
        user: {
          id: 'user-2',
          email: 'google@example.com',
          display_name: 'Google User',
          provider: 'google',
        },
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()

    await waitFor(() => {
      expect(findCall(mockedFetch, AUTH_GOOGLE_URL)).toBeTruthy()
    })
    await waitForStartupFetches(mockedFetch)
    expect(window.location.search).toBe('')

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    expect(screen.getByText('Google User (google@example.com)')).toBeInTheDocument()
  })
})
