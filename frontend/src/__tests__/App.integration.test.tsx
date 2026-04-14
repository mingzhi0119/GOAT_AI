/* @vitest-environment jsdom */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { buildApiUrl } from '../api/urls'
import { AppearanceProvider } from '../hooks/useAppearance'

const AUTH_SESSION_URL = buildApiUrl('/auth/session')
const AUTH_LOGIN_URL = buildApiUrl('/auth/login')
const AUTH_LOGOUT_URL = buildApiUrl('/auth/logout')
const MODELS_URL = buildApiUrl('/models')
const MODEL_CAPABILITIES_URL_PREFIX = buildApiUrl('/models/capabilities')
const HISTORY_URL = buildApiUrl('/history')
const SYSTEM_FEATURES_URL = buildApiUrl('/system/features')
const SYSTEM_GPU_URL = buildApiUrl('/system/gpu')
const SYSTEM_INFERENCE_URL = buildApiUrl('/system/inference')
const CHAT_URL = buildApiUrl('/chat')

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
  authSession?: { auth_required: boolean; authenticated: boolean; expires_at: string | null }
  loginSession?: { auth_required: boolean; authenticated: boolean; expires_at: string | null }
}) {
  const authSession = options?.authSession ?? {
    auth_required: false,
    authenticated: false,
    expires_at: null,
  }
  const loginSession = options?.loginSession ?? {
    auth_required: true,
    authenticated: true,
    expires_at: '2026-05-13T20:00:00Z',
  }

  return vi.fn().mockImplementation((input: string, init?: RequestInit) => {
    if (input === AUTH_SESSION_URL) {
      return Promise.resolve(buildJsonResponse(authSession))
    }
    if (input === AUTH_LOGIN_URL) {
      return Promise.resolve(buildJsonResponse(loginSession))
    }
    if (input === AUTH_LOGOUT_URL) {
      return Promise.resolve({ ok: true })
    }
    if (input === MODELS_URL) {
      return Promise.resolve(buildJsonResponse({ models: ['gemma4:26b'] }))
    }
    if (input.startsWith(MODEL_CAPABILITIES_URL_PREFIX)) {
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
    if (input === HISTORY_URL) {
      if (init?.method === 'DELETE') {
        return Promise.resolve(buildJsonResponse({}))
      }
      return Promise.resolve(buildJsonResponse({ sessions: [] }))
    }
    if (input === SYSTEM_FEATURES_URL) {
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
    if (input === SYSTEM_GPU_URL) {
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
    if (input === SYSTEM_INFERENCE_URL) {
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
    if (input === CHAT_URL) {
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
    if (calledUrl !== url) return false
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
    localStorage.clear()
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
      authSession: {
        auth_required: true,
        authenticated: false,
        expires_at: null,
      },
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()

    await screen.findByLabelText('Password')
    expect(screen.getByRole('button', { name: /enter goat/i })).toBeInTheDocument()
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
      authSession: {
        auth_required: true,
        authenticated: false,
        expires_at: null,
      },
      loginSession: {
        auth_required: true,
        authenticated: true,
        expires_at: '2026-05-13T20:00:00Z',
      },
    })
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await screen.findByLabelText('Password')
    expect(findCall(mockedFetch, MODELS_URL)).toBeFalsy()

    fireEvent.change(screen.getByLabelText('Password'), {
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

    await screen.findByLabelText('Password')
    expect(findCall(mockedFetch, AUTH_LOGOUT_URL)?.[1]).toMatchObject({
      credentials: 'same-origin',
      method: 'POST',
    })
    expect(localStorage.getItem('goat-ai-messages')).toBeNull()
    expect(localStorage.getItem('goat-ai-session-id')).toBeNull()
  })
})
