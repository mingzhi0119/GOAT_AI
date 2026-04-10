import { useCallback, useMemo, useState } from 'react'
import type { ChartSpec, OllamaOptionsPayload } from '../api/types'
import { useChat } from './useChat'
import { useFileContext, type FileBindingMode, type FileContextItem } from './useFileContext'
import { useHistory } from './useHistory'
import { historyKnowledgeAttachments } from '../utils/sessionHistory'
import { normalizeSessionTitle, truncateSessionTitle } from '../utils/sessionTitle'

interface UseChatSessionArgs {
  selectedModel: string
  userName: string
  systemInstruction: string
  ollamaOptions?: OllamaOptionsPayload
}

export interface UseChatSessionReturn {
  messages: ReturnType<typeof useChat>['messages']
  isStreaming: boolean
  sessionId: string | null
  sessionTitle: string | null
  chartSpec: ChartSpec | null
  fileContexts: FileContextItem[]
  activeFileContext: FileContextItem | null
  historySessions: ReturnType<typeof useHistory>['sessions']
  isLoadingHistory: boolean
  historyError: string | null
  sendMessage: (content: string, imageAttachmentIds?: string[]) => Promise<void>
  stopStreaming: () => void
  clearChatSession: () => void
  loadHistorySession: (sessionId: string) => Promise<void>
  deleteHistorySession: (sessionId: string) => Promise<void>
  deleteAllHistory: () => Promise<void>
  refreshHistory: () => Promise<void>
  upsertFileContext: (ctx: {
    id?: string
    filename: string
    documentId?: string
    ingestionId?: string
    retrievalMode?: string
    suffixPrompt?: string
    templatePrompt?: string
    bindingMode?: FileBindingMode
    status?: 'processing' | 'ready'
  }) => FileContextItem
  setFileContextBindingMode: (id: string, mode: FileBindingMode) => void
  removeFileContext: (id: string) => void
  clearFileContextSession: () => void
}

export function useChatSession({
  selectedModel,
  userName,
  systemInstruction,
  ollamaOptions,
}: UseChatSessionArgs): UseChatSessionReturn {
  const chat = useChat()
  const history = useHistory()
  const {
    fileContexts,
    activeFileContext,
    upsertFileContext,
    setFileContextMode,
    removeFileContext,
    replaceFileContexts,
    clearFileContext,
  } = useFileContext()
  const [chartSpec, setChartSpec] = useState<ChartSpec | null>(null)

  const sessionTitle = useMemo(() => {
    const sessionId = chat.sessionId
    if (!sessionId) return null
    const fromHistory = history.sessions.find(session => session.id === sessionId)?.title?.trim()
    if (fromHistory) return fromHistory
    const firstUser = chat.messages.find(
      message =>
        message.role === 'user' &&
        !message.isStreaming &&
        !message.hidden &&
        message.content.trim().length > 0,
    )
    if (!firstUser) return null
    return truncateSessionTitle(firstUser.content)
  }, [chat.messages, chat.sessionId, history.sessions])

  const clearChatSession = useCallback(() => {
    chat.clearMessages()
    clearFileContext()
    setChartSpec(null)
  }, [chat, clearFileContext])

  const clearFileContextSession = useCallback(() => {
    clearFileContext()
    chat.clearMessages()
    setChartSpec(null)
  }, [chat, clearFileContext])

  const setFileContextBindingMode = useCallback(
    (id: string, mode: FileBindingMode) => {
      setFileContextMode(id, mode)
    },
    [setFileContextMode],
  )

  const loadHistorySession = useCallback(
    async (sessionId: string) => {
      const session = await history.loadSession(sessionId)
      setChartSpec(session.chart_spec)
      chat.loadSession(session)
      const attachments = historyKnowledgeAttachments(session)
      if (attachments.length > 0) replaceFileContexts(attachments)
      else clearFileContext()
    },
    [chat, clearFileContext, history, replaceFileContexts],
  )

  const sendMessage = useCallback(
    async (content: string, imageAttachmentIds?: string[]) => {
      const activeSessionId = chat.sessionId ?? crypto.randomUUID()
      const optimisticTitle = normalizeSessionTitle(content) || 'New Chat'
      const nowIso = new Date().toISOString()
      history.upsertSession({
        id: activeSessionId,
        title: optimisticTitle,
        model: selectedModel,
        created_at: nowIso,
        updated_at: nowIso,
      })

      const knowledgeDocumentIds = fileContexts
        .filter(item => item.documentId && item.bindingMode !== 'idle')
        .map(item => item.documentId!)

      const shouldAttachKnowledge = knowledgeDocumentIds.length > 0 && !imageAttachmentIds?.length
      await chat.sendMessage(
        content,
        selectedModel,
        userName,
        shouldAttachKnowledge ? knowledgeDocumentIds : undefined,
        systemInstruction,
        ollamaOptions,
        setChartSpec,
        imageAttachmentIds,
        activeSessionId,
      )
      fileContexts
        .filter(item => item.bindingMode === 'single')
        .forEach(item => setFileContextMode(item.id, 'idle'))
      await history.refresh()
    },
    [
      chat,
      fileContexts,
      history,
      ollamaOptions,
      selectedModel,
      setFileContextMode,
      systemInstruction,
      userName,
    ],
  )

  return {
    messages: chat.messages,
    isStreaming: chat.isStreaming,
    sessionId: chat.sessionId,
    sessionTitle,
    chartSpec,
    fileContexts,
    activeFileContext,
    historySessions: history.sessions,
    isLoadingHistory: history.isLoading,
    historyError: history.error,
    sendMessage,
    stopStreaming: chat.stopStreaming,
    clearChatSession,
    loadHistorySession,
    deleteHistorySession: history.deleteSession,
    deleteAllHistory: history.deleteAll,
    refreshHistory: history.refresh,
    upsertFileContext,
    setFileContextBindingMode,
    removeFileContext,
    clearFileContextSession,
  }
}
