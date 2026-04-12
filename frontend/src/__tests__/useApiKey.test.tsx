/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { API_KEY_STORAGE_KEY, OWNER_ID_STORAGE_KEY, buildApiHeaders } from '../api/auth'
import { useApiKey } from '../hooks/useApiKey'

describe('useApiKey', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('hydrates from storage and persists trimmed values', () => {
    localStorage.setItem(API_KEY_STORAGE_KEY, '  secret-key  ')

    const { result } = renderHook(() => useApiKey())
    expect(result.current.apiKey).toBe('secret-key')

    act(() => {
      result.current.setApiKey('  next-key  ')
    })

    expect(result.current.apiKey).toBe('  next-key  ')
    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBe('next-key')
    expect(buildApiHeaders({ Accept: 'application/json' })).toEqual({
      Accept: 'application/json',
      'X-GOAT-API-Key': 'next-key',
    })
  })

  it('includes a stored owner id alongside the shared API key', () => {
    localStorage.setItem(OWNER_ID_STORAGE_KEY, 'owner-123')

    const { result } = renderHook(() => useApiKey())
    expect(result.current.apiKey).toBe('')

    act(() => {
      result.current.setApiKey('secret')
    })

    expect(buildApiHeaders()).toEqual({
      'X-GOAT-API-Key': 'secret',
      'X-GOAT-Owner-Id': 'owner-123',
    })
  })

  it('caps the stored key length at the UI limit', () => {
    const { result } = renderHook(() => useApiKey())
    const oversized = 'x'.repeat(300)

    act(() => {
      result.current.setApiKey(oversized)
    })

    expect(result.current.apiKey).toHaveLength(256)
    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toHaveLength(256)
  })
})
