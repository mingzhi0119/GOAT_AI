import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useChat } from '../hooks/useChat'

describe('useChat', () => {
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
})
