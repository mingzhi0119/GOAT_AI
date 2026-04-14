/* @vitest-environment jsdom */
import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useModels } from '../hooks/useModels'
import { fetchModelCapabilities, fetchModels } from '../api/models'

vi.mock('../api/models', () => ({
  fetchModels: vi.fn(),
  fetchModelCapabilities: vi.fn(),
}))

describe('useModels', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('prefers the repo default model and loads capabilities', async () => {
    vi.mocked(fetchModels).mockResolvedValue(['llama3:8b', 'qwen3:4b'])
    vi.mocked(fetchModelCapabilities).mockResolvedValue({
      model: 'qwen3:4b',
      capabilities: ['completion', 'thinking'],
      supports_tool_calling: false,
      supports_chart_tools: false,
      supports_vision: false,
      supports_thinking: true,
      context_length: 8192,
    })

    const { result } = renderHook(() => useModels())

    await waitFor(() => {
      expect(result.current.selectedModel).toBe('qwen3:4b')
    })
    expect(result.current.models).toEqual(['llama3:8b', 'qwen3:4b'])
    expect(fetchModelCapabilities).toHaveBeenCalledWith('qwen3:4b')
    expect(result.current.capabilities?.supports_thinking).toBe(true)
  })

  it('preserves an explicit model selection across refreshes', async () => {
    vi.mocked(fetchModels).mockResolvedValue(['qwen3:4b', 'backup-model'])
    vi.mocked(fetchModelCapabilities).mockResolvedValue({
      model: 'qwen3:4b',
      capabilities: ['completion'],
      supports_tool_calling: false,
      supports_chart_tools: false,
      supports_vision: false,
      supports_thinking: false,
      context_length: null,
    })

    const { result } = renderHook(() => useModels())
    await waitFor(() => expect(result.current.selectedModel).toBe('qwen3:4b'))

    vi.mocked(fetchModelCapabilities).mockResolvedValue({
      model: 'backup-model',
      capabilities: ['completion', 'vision'],
      supports_tool_calling: false,
      supports_chart_tools: false,
      supports_vision: true,
      supports_thinking: false,
      context_length: 4096,
    })

    act(() => {
      result.current.setSelectedModel('backup-model')
    })
    await waitFor(() => expect(result.current.capabilities?.model).toBe('backup-model'))

    await act(async () => {
      result.current.refresh()
    })
    await waitFor(() => expect(result.current.selectedModel).toBe('backup-model'))
  })

  it('surfaces capability fetch failures without leaving stale capabilities', async () => {
    vi.mocked(fetchModels).mockResolvedValue(['llama3:8b'])
    vi.mocked(fetchModelCapabilities).mockRejectedValue(new Error('capabilities down'))

    const { result } = renderHook(() => useModels())

    await waitFor(() => expect(result.current.selectedModel).toBe('llama3:8b'))
    await waitFor(() => expect(result.current.capabilitiesError).toBe('capabilities down'))
    expect(result.current.capabilities).toBeNull()
  })
})
