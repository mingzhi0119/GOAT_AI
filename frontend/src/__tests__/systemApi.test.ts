import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import {
  fetchDesktopDiagnostics,
  fetchGpuStatus,
  fetchInferenceLatency,
  fetchSystemFeatures,
} from '../api/system'
import { buildApiUrl } from '../api/urls'

describe('system api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('fetches gpu status payload', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        available: true,
        active: true,
        message: 'ok',
        name: 'A100',
        uuid: 'GPU-abc',
        utilization_gpu: 40,
        memory_used_mb: 1000,
        memory_total_mb: 81920,
        temperature_c: 33,
        power_draw_w: 50,
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)
    const payload = await fetchGpuStatus()
    expect(payload.available).toBe(true)
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/system/gpu'),
      expect.objectContaining({
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('fetches inference latency payload', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        chat_avg_ms: 1200.5,
        chat_sample_count: 3,
        chat_p50_ms: 1100,
        chat_p95_ms: 1500,
        first_token_avg_ms: 220,
        first_token_sample_count: 3,
        first_token_p50_ms: 200,
        first_token_p95_ms: 260,
        model_buckets: {
          'gemma4:26b': {
            chat_avg_ms: 1200.5,
            chat_p50_ms: 1100,
            chat_p95_ms: 1500,
            chat_sample_count: 3,
            first_token_avg_ms: 220,
            first_token_p50_ms: 200,
            first_token_p95_ms: 260,
            first_token_sample_count: 3,
          },
        },
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)
    const payload = await fetchInferenceLatency()
    expect(payload.chat_sample_count).toBe(3)
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/system/inference'),
      expect.objectContaining({
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('fetches system features payload', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        code_sandbox: {
          policy_allowed: false,
          allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: null,
        },
        workbench: {
          agent_tasks: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
          plan_mode: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
          browse: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
          deep_research: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
          artifact_workspace: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
          artifact_exports: {
            allowed_by_config: false,
            available_on_host: true,
            effective_enabled: false,
            deny_reason: 'permission_denied',
          },
          project_memory: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
          connectors: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
            deny_reason: null,
          },
        },
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)
    const payload = await fetchSystemFeatures()
    expect(payload.code_sandbox.policy_allowed).toBe(false)
    expect(payload.workbench.agent_tasks.effective_enabled).toBe(true)
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/system/features'),
      expect.objectContaining({
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })

  it('normalizes missing deny reasons in system feature payloads', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        code_sandbox: {
          policy_allowed: true,
          allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
        },
        workbench: {
          agent_tasks: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
          },
          plan_mode: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
          },
          browse: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
          },
          deep_research: {
            allowed_by_config: true,
            available_on_host: false,
            effective_enabled: false,
          },
          artifact_workspace: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
          },
          artifact_exports: {
            allowed_by_config: false,
            available_on_host: true,
            effective_enabled: false,
          },
          project_memory: {
            allowed_by_config: true,
            available_on_host: false,
            effective_enabled: false,
          },
          connectors: {
            allowed_by_config: true,
            available_on_host: true,
            effective_enabled: true,
          },
        },
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const payload = await fetchSystemFeatures()

    expect(payload.code_sandbox.deny_reason).toBeNull()
    expect(payload.workbench.deep_research.deny_reason).toBeNull()
  })

  it('normalizes optional desktop diagnostics fields', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        desktop_mode: false,
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    const payload = await fetchDesktopDiagnostics()

    expect(payload.failing_checks).toEqual([])
    expect(payload.skipped_checks).toEqual([])
    expect(payload.backend_base_url).toBeNull()
    expect(payload.readiness_ok).toBeNull()
  })

  it('rejects malformed system features payloads', async () => {
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        code_sandbox: {
          policy_allowed: 'yes',
          allowed_by_config: true,
          available_on_host: true,
          effective_enabled: true,
          provider_name: 'docker',
          isolation_level: 'container',
          network_policy_enforced: true,
          deny_reason: null,
        },
        workbench: {},
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)

    await expect(fetchSystemFeatures()).rejects.toThrow(
      /System features API returned an invalid response payload/,
    )
  })

  it('rejects malformed gpu and diagnostics payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            available: 'yes',
            active: true,
            message: 'ok',
            name: 'A100',
            uuid: 'GPU-abc',
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            desktop_mode: true,
            failing_checks: 'bad',
          }),
        }),
    )

    await expect(fetchGpuStatus()).rejects.toThrow(
      /GPU status API returned an invalid response payload/,
    )
    await expect(fetchDesktopDiagnostics()).rejects.toThrow(
      /Desktop diagnostics API returned an invalid response payload/,
    )
  })

  it('fetches desktop diagnostics payload', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        desktop_mode: true,
        backend_base_url: 'http://127.0.0.1:62606',
        readiness_ok: true,
        failing_checks: [],
        skipped_checks: [],
        code_sandbox_effective_enabled: true,
        workbench_effective_enabled: false,
        app_data_dir: 'C:/GOAT/Desktop',
        runtime_root: 'C:/GOAT/Desktop',
        data_dir: 'C:/GOAT/Desktop/data',
        log_dir: 'C:/GOAT/Desktop/logs',
        log_db_path: 'C:/GOAT/Desktop/chat_logs.db',
        packaged_shell_log_path: 'C:/GOAT/Desktop/logs/desktop-shell.log',
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)
    const payload = await fetchDesktopDiagnostics()
    expect(payload.desktop_mode).toBe(true)
    expect(payload.packaged_shell_log_path).toContain('desktop-shell.log')
    expect(mockedFetch).toHaveBeenCalledWith(
      buildApiUrl('/system/desktop'),
      expect.objectContaining({
        credentials: 'same-origin',
        headers: {},
      }),
    )
  })
})
