import { useCallback, useState } from 'react'

const STORAGE_KEY = 'goat-ai-file-context'

export interface FileContext {
  filename: string
  documentId?: string
  ingestionId?: string
  retrievalMode?: string
  suffixPrompt?: string
  templatePrompt?: string
  bindingMode: 'idle' | 'single' | 'persistent'
}

export interface FileContextUpdate {
  filename: string
  documentId?: string
  ingestionId?: string
  retrievalMode?: string
  suffixPrompt?: string
  templatePrompt?: string
  bindingMode?: 'idle' | 'single' | 'persistent'
}

export interface UseFileContextReturn {
  fileContext: FileContext | null
  setFileContext: (ctx: FileContextUpdate) => void
  clearFileContext: () => void
}

function loadInitial(): FileContext | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<FileContext>
    if (
      typeof parsed.filename !== 'string' ||
      (parsed.documentId !== undefined && typeof parsed.documentId !== 'string') ||
      (parsed.ingestionId !== undefined && typeof parsed.ingestionId !== 'string') ||
      (parsed.retrievalMode !== undefined && typeof parsed.retrievalMode !== 'string') ||
      (parsed.suffixPrompt !== undefined && typeof parsed.suffixPrompt !== 'string') ||
      (parsed.templatePrompt !== undefined && typeof parsed.templatePrompt !== 'string') ||
      (parsed.bindingMode !== undefined &&
        parsed.bindingMode !== 'idle' &&
        parsed.bindingMode !== 'single' &&
        parsed.bindingMode !== 'persistent')
    ) {
      return null
    }
    return {
      filename: parsed.filename,
      ...(parsed.documentId ? { documentId: parsed.documentId } : {}),
      ...(parsed.ingestionId ? { ingestionId: parsed.ingestionId } : {}),
      ...(parsed.retrievalMode ? { retrievalMode: parsed.retrievalMode } : {}),
      ...(parsed.suffixPrompt ? { suffixPrompt: parsed.suffixPrompt } : {}),
      ...(parsed.templatePrompt ? { templatePrompt: parsed.templatePrompt } : {}),
      bindingMode:
        parsed.bindingMode === 'persistent' || parsed.bindingMode === 'idle'
          ? parsed.bindingMode
          : 'single',
    }
  } catch {
    return null
  }
}

export function useFileContext(): UseFileContextReturn {
  const [fileContext, setFileContextState] = useState<FileContext | null>(loadInitial)

  const setFileContext = useCallback((ctx: FileContextUpdate) => {
    const next: FileContext = {
      ...ctx,
      bindingMode: ctx.bindingMode ?? 'single',
    }
    setFileContextState(next)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  }, [])

  const clearFileContext = useCallback(() => {
    setFileContextState(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return { fileContext, setFileContext, clearFileContext }
}
