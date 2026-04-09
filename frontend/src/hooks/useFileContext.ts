import { useCallback, useMemo, useState } from 'react'

const STORAGE_KEY = 'goat-ai-file-context'

export type FileBindingMode = 'idle' | 'single' | 'persistent'
export type FileUploadStatus = 'processing' | 'ready'

export interface FileContextItem {
  id: string
  filename: string
  documentId?: string
  ingestionId?: string
  retrievalMode?: string
  suffixPrompt?: string
  templatePrompt?: string
  bindingMode: FileBindingMode
  status: FileUploadStatus
}

export interface FileContextUpdate {
  id?: string
  filename: string
  documentId?: string
  ingestionId?: string
  retrievalMode?: string
  suffixPrompt?: string
  templatePrompt?: string
  bindingMode?: FileBindingMode
  status?: FileUploadStatus
}

export interface UseFileContextReturn {
  fileContexts: FileContextItem[]
  activeFileContext: FileContextItem | null
  upsertFileContext: (ctx: FileContextUpdate) => FileContextItem
  setFileContextMode: (id: string, mode: FileBindingMode) => void
  removeFileContext: (id: string) => void
  replaceFileContexts: (items: FileContextItem[]) => void
  clearFileContext: () => void
}

function isBindingMode(value: unknown): value is FileBindingMode {
  return value === 'idle' || value === 'single' || value === 'persistent'
}

function isUploadStatus(value: unknown): value is FileUploadStatus {
  return value === 'processing' || value === 'ready'
}

function normalizeItem(raw: Partial<FileContextItem>): FileContextItem | null {
  if (typeof raw.filename !== 'string' || raw.filename.trim() === '') return null
  if (raw.documentId !== undefined && typeof raw.documentId !== 'string') return null
  if (raw.ingestionId !== undefined && typeof raw.ingestionId !== 'string') return null
  if (raw.retrievalMode !== undefined && typeof raw.retrievalMode !== 'string') return null
  if (raw.suffixPrompt !== undefined && typeof raw.suffixPrompt !== 'string') return null
  if (raw.templatePrompt !== undefined && typeof raw.templatePrompt !== 'string') return null

  return {
    id: typeof raw.id === 'string' && raw.id.trim() ? raw.id : crypto.randomUUID(),
    filename: raw.filename,
    ...(raw.documentId ? { documentId: raw.documentId } : {}),
    ...(raw.ingestionId ? { ingestionId: raw.ingestionId } : {}),
    ...(raw.retrievalMode ? { retrievalMode: raw.retrievalMode } : {}),
    ...(raw.suffixPrompt ? { suffixPrompt: raw.suffixPrompt } : {}),
    ...(raw.templatePrompt ? { templatePrompt: raw.templatePrompt } : {}),
    bindingMode: isBindingMode(raw.bindingMode) ? raw.bindingMode : 'single',
    status: isUploadStatus(raw.status) ? raw.status : raw.documentId ? 'ready' : 'processing',
  }
}

function loadInitial(): FileContextItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    if (Array.isArray(parsed)) {
      return parsed
        .map(item => normalizeItem(item as Partial<FileContextItem>))
        .filter((item): item is FileContextItem => item !== null)
    }

    if (typeof parsed === 'object' && parsed !== null) {
      const single = normalizeItem(parsed as Partial<FileContextItem>)
      return single ? [single] : []
    }
    return []
  } catch {
    return []
  }
}

function store(items: FileContextItem[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
}

function matchIndex(items: FileContextItem[], next: FileContextUpdate): number {
  if (next.id) {
    const byId = items.findIndex(item => item.id === next.id)
    if (byId >= 0) return byId
  }
  if (next.documentId) {
    const byDocument = items.findIndex(item => item.documentId === next.documentId)
    if (byDocument >= 0) return byDocument
  }
  return items.findIndex(item => item.filename === next.filename && item.status === 'processing')
}

export function useFileContext(): UseFileContextReturn {
  const [fileContexts, setFileContexts] = useState<FileContextItem[]>(loadInitial)

  const activeFileContext = useMemo(() => {
    return (
      fileContexts.find(item => item.documentId && item.bindingMode !== 'idle') ??
      fileContexts.find(item => item.documentId) ??
      fileContexts[0] ??
      null
    )
  }, [fileContexts])

  const upsertFileContext = useCallback((ctx: FileContextUpdate) => {
    let created: FileContextItem | null = null
    setFileContexts(prev => {
      const nextItem = normalizeItem({
        ...ctx,
        id: ctx.id ?? crypto.randomUUID(),
      })
      if (!nextItem) return prev

      const next = [...prev]
      const idx = matchIndex(next, ctx)
      if (idx >= 0) {
        const merged = normalizeItem({
          ...next[idx],
          ...ctx,
          id: next[idx]!.id,
          bindingMode: ctx.bindingMode ?? next[idx]!.bindingMode,
          status: ctx.status ?? next[idx]!.status,
        })
        if (!merged) return prev
        next[idx] = merged
        created = merged
      } else {
        next.unshift(nextItem)
        created = nextItem
      }
      store(next)
      return next
    })
    return created ?? normalizeItem(ctx) ?? {
      id: crypto.randomUUID(),
      filename: ctx.filename,
      bindingMode: ctx.bindingMode ?? 'single',
      status: ctx.status ?? 'processing',
    }
  }, [])

  const setFileContextMode = useCallback((id: string, mode: FileBindingMode) => {
    setFileContexts(prev => {
      const next = prev.map(item => (item.id === id ? { ...item, bindingMode: mode } : item))
      store(next)
      return next
    })
  }, [])

  const removeFileContext = useCallback((id: string) => {
    setFileContexts(prev => {
      const next = prev.filter(item => item.id !== id)
      if (next.length > 0) store(next)
      else localStorage.removeItem(STORAGE_KEY)
      return next
    })
  }, [])

  const replaceFileContexts = useCallback((items: FileContextItem[]) => {
    const next = items
      .map(item => normalizeItem(item))
      .filter((item): item is FileContextItem => item !== null)
    setFileContexts(next)
    if (next.length > 0) store(next)
    else localStorage.removeItem(STORAGE_KEY)
  }, [])

  const clearFileContext = useCallback(() => {
    setFileContexts([])
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return {
    fileContexts,
    activeFileContext,
    upsertFileContext,
    setFileContextMode,
    removeFileContext,
    replaceFileContexts,
    clearFileContext,
  }
}
