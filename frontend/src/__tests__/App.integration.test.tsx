/* @vitest-environment jsdom */
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { buildApiUrl } from '../api/urls'
import { AppearanceProvider } from '../hooks/useAppearance'

const AUTH_SESSION_URL = buildApiUrl('/auth/session')
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

function buildJsonResponse(payload: unknown, ok = true) {
  return {
    ok,
    json: async () => payload,
    clone() {
      return buildJsonResponse(payload, ok)
    },
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
    clone() {
      return buildStreamResponse(chunks)
    },
  }
}

function buildFetchMock() {
  return vi.fn().mockImplementation((input: string, init?: RequestInit) => {
    if (matchesRequestUrl(input, AUTH_SESSION_URL)) {
      throw new Error('Auth bootstrap should not run in demo mode')
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

async function waitForInitialShellFetches(mockedFetch: ReturnType<typeof buildFetchMock>) {
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

describe('App demo shell integration', () => {
  afterEach(() => {
    window.history.replaceState({}, '', '/')
    localStorage.clear()
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('mounts the shell immediately without browser auth bootstrap', async () => {
    const mockedFetch = buildFetchMock()
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await waitForInitialShellFetches(mockedFetch)

    expect(findCall(mockedFetch, AUTH_SESSION_URL)).toBeFalsy()
    expect(screen.queryByLabelText('Shared password')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()
  })

  it('scrubs stale protected-access storage and omits auth headers', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'owner-42')
    const mockedFetch = buildFetchMock()
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await waitForInitialShellFetches(mockedFetch)

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
      })
      const headers = new Headers((call?.[1] as RequestInit | undefined)?.headers)
      expect(headers.has('X-GOAT-API-Key')).toBe(false)
      expect(headers.has('X-GOAT-Owner-Id')).toBe(false)
    }
    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toBeNull()
  })
})
