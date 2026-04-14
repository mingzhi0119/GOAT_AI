import { afterEach, describe, expect, it, vi } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { fetchModelCapabilities, fetchModels } from '../api/models'
import { buildApiUrl } from '../api/urls'

describe('models api', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('fetches model list and model capabilities', async () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-123')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')
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
    expect(mockedFetch).toHaveBeenNthCalledWith(1, buildApiUrl('/models'), {
      headers: {
        'X-GOAT-API-Key': 'secret-123',
        'X-GOAT-Owner-Id': 'alice',
      },
    })
    expect(mockedFetch).toHaveBeenNthCalledWith(
      2,
      buildApiUrl('/models/capabilities?model=gemma4%3A26b'),
      {
      headers: {
        'X-GOAT-API-Key': 'secret-123',
        'X-GOAT-Owner-Id': 'alice',
      },
      },
    )
  })

  it('normalizes missing optional model capability fields', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          model: 'gemma4:26b',
          capabilities: ['completion'],
          supports_tool_calling: false,
          supports_chart_tools: false,
          supports_vision: false,
          supports_thinking: false,
        }),
      }),
    )

    const capabilities = await fetchModelCapabilities('gemma4:26b')

    expect(capabilities.context_length).toBeNull()
  })

  it('rejects malformed JSON payloads', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ models: [123] }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            model: 'gemma4:26b',
            capabilities: 'completion',
            supports_tool_calling: false,
            supports_chart_tools: false,
            supports_vision: false,
            supports_thinking: false,
          }),
        }),
    )

    await expect(fetchModels()).rejects.toThrow(
      /Models API returned an invalid response payload/,
    )
    await expect(fetchModelCapabilities('gemma4:26b')).rejects.toThrow(
      /Model capabilities API returned an invalid response payload/,
    )
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
