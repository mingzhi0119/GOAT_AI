import { renderHook } from '@testing-library/react'
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
})
