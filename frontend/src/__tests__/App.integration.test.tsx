/* @vitest-environment jsdom */
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { AppearanceProvider } from '../hooks/useAppearance'

function buildJsonResponse(payload: unknown) {
  return {
    ok: true,
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

function buildFetchMock() {
  return vi.fn().mockImplementation((input: string, init?: RequestInit) => {
    if (input === './api/models') {
      return Promise.resolve(buildJsonResponse({ models: ['gemma4:26b'] }))
    }
    if (input.startsWith('./api/models/capabilities')) {
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
    if (input === './api/history') {
      if (init?.method === 'DELETE') {
        return Promise.resolve(buildJsonResponse({}))
      }
      return Promise.resolve(buildJsonResponse({ sessions: [] }))
    }
    if (input === './api/system/features') {
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
    if (input === './api/system/gpu') {
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
    if (input === './api/system/inference') {
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
    if (input === './api/chat') {
      return Promise.resolve(
        buildStreamResponse(['data: {"type":"token","token":"Hello back"}\n\n', 'data: {"type":"done"}\n\n']),
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
    expect(findCall(mockedFetch, './api/models')).toBeTruthy()
    expect(findCall(mockedFetch, './api/history')).toBeTruthy()
    expect(findCall(mockedFetch, './api/system/features')).toBeTruthy()
    expect(findCall(mockedFetch, './api/system/gpu')).toBeTruthy()
    expect(findCall(mockedFetch, './api/system/inference')).toBeTruthy()
  })
}

function renderApp() {
  return render(
    <AppearanceProvider>
      <App />
    </AppearanceProvider>,
  )
}

describe('App protected access integration', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('uses persisted protected-access headers for startup API calls', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'owner-42')
    const mockedFetch = buildFetchMock()
    vi.stubGlobal('fetch', mockedFetch)

    renderApp()
    await waitForStartupFetches(mockedFetch)

    for (const url of [
      './api/models',
      './api/history',
      './api/system/features',
      './api/system/gpu',
      './api/system/inference',
    ]) {
      const call = findCall(mockedFetch, url)
      expect(call?.[1]).toMatchObject({
        headers: {
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'owner-42',
        },
      })
    }
  })

  it('persists protected access from settings and reuses it for chat after refresh', async () => {
    const mockedFetch = buildFetchMock()
    vi.stubGlobal('fetch', mockedFetch)

    const firstRender = renderApp()
    await waitForStartupFetches(mockedFetch)

    fireEvent.click(screen.getByRole('button', { name: /settings/i }))
    fireEvent.change(screen.getByLabelText('API key'), { target: { value: 'secret-abc' } })
    fireEvent.change(screen.getByLabelText('Owner ID'), { target: { value: 'owner-99' } })

    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBe('secret-abc')
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toBe('owner-99')

    firstRender.unmount()
    mockedFetch.mockClear()

    renderApp()
    await waitForStartupFetches(mockedFetch)

    fireEvent.change(screen.getByPlaceholderText('Message GOAT'), {
      target: { value: 'Hello protected world' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }))

    await waitFor(() => {
      expect(findCall(mockedFetch, './api/chat')).toBeTruthy()
    })

    expect(findCall(mockedFetch, './api/chat')?.[1]).toMatchObject({
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-GOAT-API-Key': 'secret-abc',
        'X-GOAT-Owner-Id': 'owner-99',
      },
    })
    const assistantReplies = await screen.findAllByText(/^Hello back$/i, undefined, {
      timeout: 5000,
    })
    expect(assistantReplies.length).toBeGreaterThan(0)
  })
})
