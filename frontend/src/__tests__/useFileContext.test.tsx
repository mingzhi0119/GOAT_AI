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

  it('stores, merges, and clears file context in localStorage', () => {
    const { result } = renderHook(() => useFileContext())

    act(() => {
      result.current.setFileContext({
        filename: 'data.csv',
        suffixPrompt: 'Inspect this CSV for trends, anomalies, and key comparisons.',
      })
    })

    expect(result.current.fileContext?.filename).toBe('data.csv')
    expect(result.current.fileContext?.suffixPrompt).toContain('CSV')
    expect(result.current.fileContext?.bindingMode).toBe('single')
    expect(localStorage.getItem('goat-ai-file-context')).toContain('data.csv')

    act(() => {
      result.current.setFileContext({
        filename: 'data.csv',
        documentId: 'doc-1',
        ingestionId: 'ing-1',
        retrievalMode: 'knowledge_rag',
        suffixPrompt: 'Inspect this CSV for trends, anomalies, and key comparisons.',
        templatePrompt: 'Analyze this CSV and tell me the main trends, outliers, and comparisons worth noting.',
      })
    })

    expect(result.current.fileContext?.documentId).toBe('doc-1')
    expect(result.current.fileContext?.templatePrompt).toContain('Analyze this CSV')
    expect(result.current.fileContext?.suffixPrompt).toContain('CSV')
    expect(result.current.fileContext?.bindingMode).toBe('single')

    act(() => {
      result.current.clearFileContext()
    })

    expect(result.current.fileContext).toBeNull()
    expect(localStorage.getItem('goat-ai-file-context')).toBeNull()
  })
})
