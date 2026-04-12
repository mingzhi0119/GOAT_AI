import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import {
  fetchDesktopDiagnostics,
  fetchGpuStatus,
  fetchInferenceLatency,
  fetchSystemFeatures,
} from '../api/system'

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
    expect(mockedFetch).toHaveBeenCalledWith('./api/system/gpu', {
      headers: {
        'X-GOAT-API-Key': 'secret-123',
        'X-GOAT-Owner-Id': 'alice',
      },
    })
  })

  it('fetches inference latency payload', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
    const mockedFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        chat_avg_ms: 1200.5,
        chat_sample_count: 3,
      }),
    })
    vi.stubGlobal('fetch', mockedFetch)
    const payload = await fetchInferenceLatency()
    expect(payload.chat_sample_count).toBe(3)
    expect(mockedFetch).toHaveBeenCalledWith('./api/system/inference', {
      headers: {
        'X-GOAT-API-Key': 'secret-123',
        'X-GOAT-Owner-Id': 'alice',
      },
    })
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
    expect(mockedFetch).toHaveBeenCalledWith('./api/system/features', {
      headers: {
        'X-GOAT-API-Key': 'secret-123',
        'X-GOAT-Owner-Id': 'alice',
      },
    })
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
    expect(mockedFetch).toHaveBeenCalledWith('./api/system/desktop', {
      headers: {
        'X-GOAT-API-Key': 'secret-123',
        'X-GOAT-Owner-Id': 'alice',
      },
    })
  })
})
