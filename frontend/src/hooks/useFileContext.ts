import { useCallback, useState } from 'react'

const STORAGE_KEY = 'goat-ai-file-context'

export interface FileContext {
  filename: string
  documentId: string
  ingestionId: string
  retrievalMode: string
}

export interface UseFileContextReturn {
  fileContext: FileContext | null
  setFileContext: (ctx: FileContext) => void
  clearFileContext: () => void
}

function loadInitial(): FileContext | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<FileContext>
    if (
      typeof parsed.filename !== 'string' ||
      typeof parsed.documentId !== 'string' ||
      typeof parsed.ingestionId !== 'string' ||
      typeof parsed.retrievalMode !== 'string'
    ) {
      return null
    }
    return {
      filename: parsed.filename,
      documentId: parsed.documentId,
      ingestionId: parsed.ingestionId,
      retrievalMode: parsed.retrievalMode,
    }
  } catch {
    return null
  }
}

export function useFileContext(): UseFileContextReturn {
  const [fileContext, setFileContextState] = useState<FileContext | null>(loadInitial)

  const setFileContext = useCallback((ctx: FileContext) => {
    setFileContextState(ctx)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ctx))
  }, [])

  const clearFileContext = useCallback(() => {
    setFileContextState(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { fileContext, setFileContext, clearFileContext }
}
