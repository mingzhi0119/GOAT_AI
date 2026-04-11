/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useSystemInstruction } from '../hooks/useSystemInstruction'

const STORAGE_KEY = 'goat-ai-system-instruction'

describe('useSystemInstruction', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('hydrates from storage and persists non-empty values', () => {
    localStorage.setItem(STORAGE_KEY, 'Use bullets.')

    const { result } = renderHook(() => useSystemInstruction())
    expect(result.current.systemInstruction).toBe('Use bullets.')

    act(() => {
      result.current.setSystemInstruction('Prefer numbered steps.')
    })

    expect(result.current.systemInstruction).toBe('Prefer numbered steps.')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('Prefer numbered steps.')
  })

  it('trims empty values out of storage and caps the maximum length', () => {
    const { result } = renderHook(() => useSystemInstruction())

    act(() => {
      result.current.setSystemInstruction('x'.repeat(9000))
    })

    expect(result.current.systemInstruction).toHaveLength(8000)

    act(() => {
      result.current.setSystemInstruction('   ')
    })

    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
  })
})
