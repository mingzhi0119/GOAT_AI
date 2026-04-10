import { renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { useAdvancedSettings } from '../hooks/useAdvancedSettings'

describe('useAdvancedSettings', () => {
  it('serializes boolean think values for chat requests', () => {
    const { result } = renderHook(() => useAdvancedSettings())

    expect(result.current.getOptionsForRequest(true).think).toBe(true)
    expect(result.current.getOptionsForRequest(false).think).toBe(false)
  })

  it('serializes reasoning levels for chat requests', () => {
    const { result } = renderHook(() => useAdvancedSettings())

    expect(result.current.getOptionsForRequest('low').think).toBe('low')
    expect(result.current.getOptionsForRequest('medium').think).toBe('medium')
    expect(result.current.getOptionsForRequest('high').think).toBe('high')
  })
})
