/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY, buildApiHeaders } from '../api/auth'
import { useApiKey } from '../hooks/useApiKey'

describe('useApiKey', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('ignores stale protected-access storage in public demo mode', () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, 'secret-key')
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'owner-123')

    const { result } = renderHook(() => useApiKey())

    expect(result.current.apiKey).toBe('')
    act(() => {
      result.current.setApiKey('next-key')
    })
    expect(result.current.apiKey).toBe('')
    expect(buildApiHeaders({ Accept: 'application/json' })).toEqual({
      Accept: 'application/json',
    })
    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(OWNER_ID_STORAGE_KEY)).toBeNull()
  })
})
