/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY } from '../api/auth'
import { useOwnerId } from '../hooks/useOwnerId'

describe('useOwnerId', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('ignores and clears stale owner state in public demo mode', () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-key')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'alice')

    const { result } = renderHook(() => useOwnerId())

    expect(result.current.ownerId).toBe('')
    act(() => {
      result.current.setOwnerId('bob')
    })
    expect(result.current.ownerId).toBe('')
    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toBeNull()
  })
})
