import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import {
  executeCodeSandbox,
  fetchCodeSandboxExecution,
  fetchCodeSandboxExecutionEvents,
  openCodeSandboxLogStream,
} from '../api/codeSandbox'
import { buildApiUrl } from '../api/urls'

describe('code sandbox api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('executes a code sandbox request', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        execution_id: 'cs-1',
        status: 'completed',
        execution_mode: 'sync',
        runtime_preset: 'shell',
        network_policy: 'disabled',
        created_at: '2026-04-10T00:00:00Z',
        updated_at: '2026-04-10T00:00:01Z',
        started_at: '2026-04-10T00:00:00Z',
        finished_at: '2026-04-10T00:00:01Z',
        provider_name: 'docker',
        isolation_level: 'container',
        network_policy_enforced: true,
        exit_code: 0,
        stdout: 'ok',
        stderr: '',
        timed_out: false,
        error_detail: null,
        output_files: [],
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const payload = await executeCodeSandbox({ code: 'echo ok' })
    expect(payload.execution_id).toBe('cs-1')
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/code-sandbox/exec'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'content-type': 'application/json',
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'alice',
        },
      }),
    )
  })

  it('parses detail from error responses', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Docker runtime is not ready.' }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    await expect(executeCodeSandbox({ code: 'echo ok' })).rejects.toThrow(
      'Docker runtime is not ready.',
    )
  })

  it('reads an execution and event timeline', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          execution_id: 'cs-1',
          status: 'completed',
          execution_mode: 'sync',
          runtime_preset: 'shell',
          network_policy: 'disabled',
          created_at: '2026-04-10T00:00:00Z',
          updated_at: '2026-04-10T00:00:01Z',
          started_at: '2026-04-10T00:00:00Z',
          finished_at: '2026-04-10T00:00:01Z',
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          exit_code: 0,
          stdout: 'ok',
          stderr: '',
          timed_out: false,
          error_detail: null,
          output_files: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          execution_id: 'cs-1',
          events: [
            {
              sequence: 1,
              event_type: 'execution.queued',
              created_at: '2026-04-10T00:00:00Z',
              status: 'queued',
              message: 'Execution accepted.',
              metadata: {},
            },
          ],
        }),
      })
    vi.stubGlobal('fetch', mockedFetch)

    const execution = await fetchCodeSandboxExecution('cs-1')
    const events = await fetchCodeSandboxExecutionEvents('cs-1')

    expect(execution.status).toBe('completed')
    expect(events.events[0]?.event_type).toBe('execution.queued')
    expect(mockedFetch).toHaveBeenNthCalledWith(
      1,
      buildApiUrl('/code-sandbox/executions/cs-1'),
      {
        credentials: 'same-origin',
        headers: {
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'alice',
        },
      },
    )
    expect(mockedFetch).toHaveBeenNthCalledWith(
      2,
      buildApiUrl('/code-sandbox/executions/cs-1/events'),
      {
        credentials: 'same-origin',
        headers: {
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'alice',
        },
      },
    )
  })

  it('normalizes optional execution and event fields', async () => {
    const mockedFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          execution_id: 'cs-2',
          status: 'running',
          execution_mode: 'async',
          runtime_preset: 'shell',
          network_policy: 'disabled',
          created_at: '2026-04-10T00:00:00Z',
          updated_at: '2026-04-10T00:00:02Z',
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          stdout: '',
          stderr: '',
          timed_out: false,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          execution_id: 'cs-2',
          events: [
            {
              sequence: 1,
              event_type: 'execution.started',
              created_at: '2026-04-10T00:00:00Z',
            },
          ],
        }),
      })
    vi.stubGlobal('fetch', mockedFetch)

    const execution = await fetchCodeSandboxExecution('cs-2')
    const events = await fetchCodeSandboxExecutionEvents('cs-2')

    expect(execution.started_at).toBeNull()
    expect(execution.exit_code).toBeNull()
    expect(execution.output_files).toEqual([])
    expect(events.events[0]).toEqual({
      sequence: 1,
      event_type: 'execution.started',
      created_at: '2026-04-10T00:00:00Z',
      status: null,
      message: null,
      metadata: {},
    })
  })

  it('rejects malformed execution payloads', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        execution_id: 123,
        status: 'completed',
        execution_mode: 'sync',
        runtime_preset: 'shell',
        network_policy: 'disabled',
        created_at: '2026-04-10T00:00:00Z',
        updated_at: '2026-04-10T00:00:01Z',
        provider_name: 'docker',
        isolation_level: 'container',
        network_policy_enforced: true,
        stdout: 'ok',
        stderr: '',
        timed_out: false,
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    await expect(fetchCodeSandboxExecution('cs-3')).rejects.toThrow(
      /Code sandbox API returned an invalid response payload/,
    )
  })

  it('rejects malformed execution event payloads', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        execution_id: 'cs-3',
        events: [
          {
            sequence: 'bad',
            event_type: 'execution.started',
            created_at: '2026-04-10T00:00:00Z',
          },
        ],
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    await expect(fetchCodeSandboxExecutionEvents('cs-3')).rejects.toThrow(
      /Code sandbox events API returned an invalid response payload/,
    )
  })

  it('opens an authenticated fetch log stream with cursor replay support', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const encoder = new TextEncoder()
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: new ReadableStream<Uint8Array>({
        start(controller) {
          controller.enqueue(
            encoder.encode(
              'data: {"type":"stdout","sequence":"bad","chunk":"ignored"}\n\n' +
                'data: {"type":"stdout","sequence":4,"chunk":"hello"}\n\n',
            ),
          )
          controller.close()
        },
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)
    const onEvent = vi.fn()
    const stop = openCodeSandboxLogStream('cs-1', { afterSequence: 3, onEvent })

    await new Promise(resolve => setTimeout(resolve, 0))

    expect(onEvent).toHaveBeenCalledWith({ type: 'stdout', sequence: 4, chunk: 'hello' })
    expect(mockedFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/code-sandbox/executions/cs-1/logs?after_seq=3'),
      expect.objectContaining({
        headers: {
          'X-GOAT-API-Key': 'secret-123',
          'X-GOAT-Owner-Id': 'alice',
        },
        signal: expect.any(AbortSignal),
      }),
    )
    stop()
  })
})
