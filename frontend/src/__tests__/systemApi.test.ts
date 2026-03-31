import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchGpuStatus } from '../api/system'

describe('system api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches gpu status payload', async () => {
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
    expect(mockedFetch).toHaveBeenCalledWith('./api/system/gpu')
  })
})
