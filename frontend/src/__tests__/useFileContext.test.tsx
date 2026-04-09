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

  it('stores, upgrades, and clears uploaded file contexts', () => {
    const { result } = renderHook(() => useFileContext())

    let processingId = ''
    act(() => {
      const created = result.current.upsertFileContext({
        filename: 'data.csv',
        suffixPrompt: 'Inspect this CSV for trends, anomalies, and key comparisons.',
        status: 'processing',
      })
      processingId = created.id
    })

    expect(result.current.fileContexts).toHaveLength(1)
    expect(result.current.fileContexts[0]?.filename).toBe('data.csv')
    expect(result.current.fileContexts[0]?.status).toBe('processing')
    expect(localStorage.getItem('goat-ai-file-context')).toContain('data.csv')

    act(() => {
      result.current.upsertFileContext({
        id: processingId,
        filename: 'data.csv',
        documentId: 'doc-1',
        ingestionId: 'ing-1',
        retrievalMode: 'knowledge_rag',
        suffixPrompt: 'Inspect this CSV for trends, anomalies, and key comparisons.',
        templatePrompt:
          'Analyze this CSV and tell me the main trends, outliers, and comparisons worth noting.',
        status: 'ready',
      })
    })

    expect(result.current.fileContexts[0]?.documentId).toBe('doc-1')
    expect(result.current.fileContexts[0]?.templatePrompt).toContain('Analyze this CSV')
    expect(result.current.fileContexts[0]?.status).toBe('ready')
    expect(result.current.activeFileContext?.documentId).toBe('doc-1')

    act(() => {
      result.current.setFileContextMode(processingId, 'persistent')
    })

    expect(result.current.fileContexts[0]?.bindingMode).toBe('persistent')

    act(() => {
      result.current.removeFileContext(processingId)
    })

    expect(result.current.fileContexts).toHaveLength(0)
    expect(localStorage.getItem('goat-ai-file-context')).toBeNull()
  })
})
