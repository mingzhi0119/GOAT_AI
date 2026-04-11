/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useChatLayoutMode } from '../hooks/useChatLayoutMode'

describe('useChatLayoutMode', () => {
  it('uses the viewport width when no explicit mode is provided', () => {
    window.innerWidth = 640

    const { result } = renderHook(() => useChatLayoutMode())
    expect(result.current.layoutMode).toBe('narrow')

    act(() => {
      window.innerWidth = 1200
      window.dispatchEvent(new Event('resize'))
    })

    expect(result.current.layoutMode).toBe('wide')
  })

  it('honors an explicit mode override', () => {
    window.innerWidth = 640

    const { result } = renderHook(() => useChatLayoutMode('wide'))
    expect(result.current.layoutMode).toBe('wide')
  })
})
