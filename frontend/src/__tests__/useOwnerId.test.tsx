/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { OWNER_ID_STORAGE_KEY } from '../api/auth'
import { useOwnerId } from '../hooks/useOwnerId'

describe('useOwnerId', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('hydrates from storage and persists trimmed values', () => {
    localStorage.setItem(OWNER_ID_STORAGE_KEY, '  alice  ')

    const { result } = renderHook(() => useOwnerId())
    expect(result.current.ownerId).toBe('alice')

    act(() => {
      result.current.setOwnerId('  bob  ')
    })

    expect(result.current.ownerId).toBe('  bob  ')
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toBe('bob')
  })

  it('caps the stored owner id length at the UI limit', () => {
    const { result } = renderHook(() => useOwnerId())
    const oversized = 'x'.repeat(300)

    act(() => {
      result.current.setOwnerId(oversized)
    })

    expect(result.current.ownerId).toHaveLength(256)
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toHaveLength(256)
  })
})
