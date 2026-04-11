import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { streamChat } from '../api/chat'
import { useChat } from '../hooks/useChat'

vi.mock('../api/chat', () => ({
  streamChat: vi.fn(),
}))

describe('useChat', () => {
  beforeEach(() => {
    vi.mocked(streamChat).mockReset()
    localStorage.clear()
  })

  it('exposes streaming controls and message list', () => {
    const { result } = renderHook(() => useChat())
    expect(Array.isArray(result.current.messages)).toBe(true)
    expect(typeof result.current.sendMessage).toBe('function')
    expect(typeof result.current.clearMessages).toBe('function')
    expect(typeof result.current.stopStreaming).toBe('function')
    expect(typeof result.current.streamToChat).toBe('function')
  })

  it('attaches artifact events to the active assistant message', async () => {
    const { result } = renderHook(() => useChat())

    async function* stream() {
      yield { type: 'token' as const, token: 'Prepared ' }
      yield {
        type: 'artifact' as const,
        artifact_id: 'art-1',
        filename: 'brief.md',
        mime_type: 'text/markdown',
        byte_size: 128,
        download_url: '/api/artifacts/art-1',
      }
      yield { type: 'done' as const }
    }

    await act(async () => {
      await result.current.streamToChat(stream())
    })

    expect(result.current.messages).toHaveLength(1)
    expect(result.current.messages[0]?.artifacts).toEqual([
      {
        artifact_id: 'art-1',
        filename: 'brief.md',
        mime_type: 'text/markdown',
        byte_size: 128,
        download_url: '/api/artifacts/art-1',
      },
    ])
  })

  it('shows thinking disclosure when reasoning level is a string', async () => {
    vi.mocked(streamChat).mockImplementation(async function* () {
      yield { type: 'thinking' as const, token: 'Reasoning trace' }
      yield { type: 'done' as const }
    })

    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage(
        'Hello',
        'test-model',
        undefined,
        undefined,
        undefined,
        undefined,
        undefined,
        { temperature: 0.8, max_tokens: 64, top_p: 0.9, think: 'medium' },
      )
    })

    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[1]?.showThinking).toBe(true)
    expect(result.current.messages[1]?.thinkingContent).toBe('Reasoning trace')
  })

  it('passes the active theme style to the chat request', async () => {
    vi.mocked(streamChat).mockImplementation(async function* () {
      yield { type: 'done' as const }
    })

    const { result } = renderHook(() => useChat())

    await act(async () => {
      await result.current.sendMessage(
        'Hello',
        'test-model',
        undefined,
        undefined,
        false,
        '',
        'thu',
      )
    })

    expect(streamChat).toHaveBeenCalledWith(
      expect.objectContaining({
        model: 'test-model',
        theme_style: 'thu',
      }),
      expect.any(Object),
    )
  })
})
