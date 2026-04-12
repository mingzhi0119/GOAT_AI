/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useGpuStatus } from '../hooks/useGpuStatus'
import { fetchGpuStatus, fetchInferenceLatency } from '../api/system'

vi.mock('../api/system', () => ({
  fetchGpuStatus: vi.fn(),
  fetchInferenceLatency: vi.fn(),
}))

async function flushAsyncEffects(): Promise<void> {
  await act(async () => {
    await Promise.resolve()
    await Promise.resolve()
  })
}

describe('useGpuStatus', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
    setVisibilityState('visible')
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('polls on the idle cadence and refreshes on demand', async () => {
    vi.mocked(fetchGpuStatus).mockResolvedValue({
      available: true,
      active: false,
      message: 'idle',
      name: 'GPU',
      uuid: 'gpu-1',
      utilization_gpu: 0,
      memory_used_mb: 0,
      memory_total_mb: 8192,
      temperature_c: 40,
      power_draw_w: 20,
    })
    vi.mocked(fetchInferenceLatency).mockResolvedValue({
      chat_avg_ms: 100,
      chat_sample_count: 1,
      chat_p50_ms: 100,
      chat_p95_ms: 100,
      first_token_avg_ms: 50,
      first_token_sample_count: 1,
      first_token_p50_ms: 50,
      first_token_p95_ms: 50,
      model_buckets: {},
    })

    const { result } = renderHook(() => useGpuStatus(false))
    await flushAsyncEffects()
    expect(result.current.status?.uuid).toBe('gpu-1')

    await act(async () => {
      await result.current.refreshNow()
    })
    await flushAsyncEffects()
    expect(fetchGpuStatus).toHaveBeenCalledTimes(2)

    await act(async () => {
      vi.advanceTimersByTime(3000)
    })
    await flushAsyncEffects()
    expect(fetchGpuStatus).toHaveBeenCalledTimes(3)
  })

  it('uses the streaming cadence and reports gpu fetch failures separately', async () => {
    vi.mocked(fetchGpuStatus).mockRejectedValue(new Error('gpu offline'))
    vi.mocked(fetchInferenceLatency).mockResolvedValue({
      chat_avg_ms: 120,
      chat_sample_count: 2,
      chat_p50_ms: 110,
      chat_p95_ms: 140,
      first_token_avg_ms: 60,
      first_token_sample_count: 2,
      first_token_p50_ms: 55,
      first_token_p95_ms: 70,
      model_buckets: {},
    })

    const { result } = renderHook(() => useGpuStatus(true))
    await flushAsyncEffects()
    expect(result.current.error).toBe('gpu offline')
    expect(result.current.status).toBeNull()
    expect(result.current.inference?.chat_sample_count).toBe(2)

    await act(async () => {
      vi.advanceTimersByTime(1000)
    })
    await flushAsyncEffects()
    expect(fetchGpuStatus).toHaveBeenCalledTimes(2)
  })

  it('stops background polling while hidden and refreshes when the page becomes visible again', async () => {
    setVisibilityState('hidden')
    vi.mocked(fetchGpuStatus).mockResolvedValue({
      available: true,
      active: false,
      message: 'idle',
      name: 'GPU',
      uuid: 'gpu-1',
      utilization_gpu: 0,
      memory_used_mb: 0,
      memory_total_mb: 8192,
      temperature_c: 40,
      power_draw_w: 20,
    })
    vi.mocked(fetchInferenceLatency).mockResolvedValue({
      chat_avg_ms: 100,
      chat_sample_count: 1,
      chat_p50_ms: 100,
      chat_p95_ms: 100,
      first_token_avg_ms: 50,
      first_token_sample_count: 1,
      first_token_p50_ms: 50,
      first_token_p95_ms: 50,
      model_buckets: {},
    })

    renderHook(() => useGpuStatus(false))
    await flushAsyncEffects()
    expect(fetchGpuStatus).toHaveBeenCalledTimes(1)

    await act(async () => {
      vi.advanceTimersByTime(9000)
    })
    await flushAsyncEffects()
    expect(fetchGpuStatus).toHaveBeenCalledTimes(1)

    setVisibilityState('visible')
    act(() => {
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await flushAsyncEffects()
    expect(fetchGpuStatus).toHaveBeenCalledTimes(2)
  })
})

function setVisibilityState(state: DocumentVisibilityState) {
  Object.defineProperty(document, 'visibilityState', {
    configurable: true,
    value: state,
  })
}
