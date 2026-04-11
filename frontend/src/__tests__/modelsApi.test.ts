import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchModelCapabilities, fetchModels } from '../api/models'

describe('models api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches model list and model capabilities', async () => {
    const mockedFetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ models: ['gemma4:26b', 'llama3:8b'] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          model: 'gemma4:26b',
          capabilities: ['completion', 'vision'],
          supports_tool_calling: false,
          supports_chart_tools: false,
          supports_vision: true,
          supports_thinking: false,
          context_length: 8192,
        }),
      })
    vi.stubGlobal('fetch', mockedFetch)

    const models = await fetchModels()
    const capabilities = await fetchModelCapabilities('gemma4:26b')

    expect(models).toEqual(['gemma4:26b', 'llama3:8b'])
    expect(capabilities.supports_vision).toBe(true)
    expect(mockedFetch).toHaveBeenNthCalledWith(2, './api/models/capabilities?model=gemma4%3A26b')
  })

  it('throws typed errors when endpoints fail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }))
    await expect(fetchModels()).rejects.toThrow('Models API: HTTP 503')

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    await expect(fetchModelCapabilities('bad-model')).rejects.toThrow(
      'Model capabilities API: HTTP 404',
    )
  })
})
