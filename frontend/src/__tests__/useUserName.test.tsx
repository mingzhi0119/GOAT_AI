/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { useUserName } from '../hooks/useUserName'

const STORAGE_KEY = 'goat-ai-username'

describe('useUserName', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('hydrates from storage and persists trimmed values', () => {
    localStorage.setItem(STORAGE_KEY, 'Simon')

    const { result } = renderHook(() => useUserName())
    expect(result.current.userName).toBe('Simon')

    act(() => {
      result.current.setUserName('  Mingzhi  ')
    })

    expect(result.current.userName).toBe('Mingzhi')
    expect(localStorage.getItem(STORAGE_KEY)).toBe('Mingzhi')
  })

  it('removes the stored value when the trimmed name is empty', () => {
    localStorage.setItem(STORAGE_KEY, 'Simon')

    const { result } = renderHook(() => useUserName())

    act(() => {
      result.current.setUserName('   ')
    })

    expect(result.current.userName).toBe('')
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
  })
})
