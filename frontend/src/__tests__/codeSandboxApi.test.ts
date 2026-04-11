import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  executeCodeSandbox,
  fetchCodeSandboxExecution,
  fetchCodeSandboxExecutionEvents,
} from '../api/codeSandbox'

describe('code sandbox api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('executes a code sandbox request', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        execution_id: 'cs-1',
        status: 'completed',
        runtime_preset: 'shell',
        network_policy: 'disabled',
        created_at: '2026-04-10T00:00:00Z',
        updated_at: '2026-04-10T00:00:01Z',
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
    expect(mockedFetch).toHaveBeenCalledWith('./api/code-sandbox/exec', expect.any(Object))
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
    const mockedFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          execution_id: 'cs-1',
          status: 'completed',
          runtime_preset: 'shell',
          network_policy: 'disabled',
          created_at: '2026-04-10T00:00:00Z',
          updated_at: '2026-04-10T00:00:01Z',
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
  })
})
