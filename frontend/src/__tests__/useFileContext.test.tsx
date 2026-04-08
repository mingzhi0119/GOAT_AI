/* @vitest-environment jsdom */
import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useFileContext } from '../hooks/useFileContext'

describe('useFileContext', () => {
  let store: Record<string, string> = {}

  beforeEach(() => {
    store = {}
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => (key in store ? store[key] : null),
      setItem: (key: string, value: string) => {
        store[key] = value
      },
      removeItem: (key: string) => {
        delete store[key]
      },
      clear: () => {
        store = {}
      },
    })
  })

  it('stores and clears file context in localStorage', () => {
    const { result } = renderHook(() => useFileContext())

    act(() => {
      result.current.setFileContext({
        filename: 'data.csv',
        documentId: 'doc-1',
        ingestionId: 'ing-1',
        retrievalMode: 'knowledge_rag',
      })
    })

    expect(result.current.fileContext?.filename).toBe('data.csv')
    expect(result.current.fileContext?.documentId).toBe('doc-1')
    expect(localStorage.getItem('goat-ai-file-context')).toContain('data.csv')

    act(() => {
      result.current.clearFileContext()
    })

    expect(result.current.fileContext).toBeNull()
    expect(localStorage.getItem('goat-ai-file-context')).toBeNull()
  })
})
