/* @vitest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDesktopDiagnostics } from '../hooks/useDesktopDiagnostics'
import { fetchDesktopDiagnostics } from '../api/system'

vi.mock('../api/system', () => ({
  fetchDesktopDiagnostics: vi.fn(),
}))

describe('useDesktopDiagnostics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads desktop diagnostics on mount and refreshes on demand', async () => {
    vi.mocked(fetchDesktopDiagnostics).mockResolvedValue({
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
    })

    const { result } = renderHook(() => useDesktopDiagnostics())

    await waitFor(() => {
      expect(result.current.diagnostics?.backend_base_url).toBe('http://127.0.0.1:62606')
    })

    await act(async () => {
      await result.current.refreshNow()
    })

    expect(fetchDesktopDiagnostics).toHaveBeenCalledTimes(2)
  })

  it('surfaces fetch errors while leaving diagnostics empty', async () => {
    vi.mocked(fetchDesktopDiagnostics).mockRejectedValue(new Error('desktop diagnostics unavailable'))

    const { result } = renderHook(() => useDesktopDiagnostics())

    await waitFor(() => {
      expect(result.current.error).toBe('desktop diagnostics unavailable')
    })
    expect(result.current.diagnostics).toBeNull()
  })
})
