/* @vitest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSystemFeatures } from '../hooks/useSystemFeatures'
import { fetchSystemFeatures } from '../api/system'

vi.mock('../api/system', () => ({
  fetchSystemFeatures: vi.fn(),
}))

describe('useSystemFeatures', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads features on mount and refreshes on demand', async () => {
    vi.mocked(fetchSystemFeatures).mockResolvedValue({
      code_sandbox: {
        policy_allowed: true,
        allowed_by_config: true,
        available_on_host: true,
        effective_enabled: true,
        provider_name: 'docker',
        isolation_level: 'container',
        network_policy_enforced: true,
        deny_reason: null,
      },
      workbench: {
        agent_tasks: { allowed_by_config: true, available_on_host: true, effective_enabled: true, deny_reason: null },
        plan_mode: { allowed_by_config: true, available_on_host: true, effective_enabled: true, deny_reason: null },
        browse: { allowed_by_config: true, available_on_host: true, effective_enabled: true, deny_reason: null },
        deep_research: { allowed_by_config: true, available_on_host: false, effective_enabled: false, deny_reason: 'not_implemented' },
        artifact_workspace: { allowed_by_config: true, available_on_host: false, effective_enabled: false, deny_reason: 'not_implemented' },
        artifact_exports: { allowed_by_config: false, available_on_host: true, effective_enabled: false, deny_reason: 'permission_denied' },
        project_memory: { allowed_by_config: true, available_on_host: false, effective_enabled: false, deny_reason: 'not_implemented' },
        connectors: { allowed_by_config: true, available_on_host: true, effective_enabled: true, deny_reason: null },
      },
    })

    const { result } = renderHook(() => useSystemFeatures())

    await waitFor(() => {
      expect(result.current.features?.code_sandbox.provider_name).toBe('docker')
    })

    await act(async () => {
      await result.current.refreshNow()
    })
    expect(fetchSystemFeatures).toHaveBeenCalledTimes(2)
  })

  it('surfaces fetch errors while leaving features empty', async () => {
    vi.mocked(fetchSystemFeatures).mockRejectedValue(new Error('feature gate unavailable'))

    const { result } = renderHook(() => useSystemFeatures())

    await waitFor(() => {
      expect(result.current.error).toBe('feature gate unavailable')
    })
    expect(result.current.features).toBeNull()
  })
})
