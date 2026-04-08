import { useCallback, useMemo, useState } from 'react'
import type { ChartSpec, OllamaOptionsPayload } from '../api/types'
import { useChat } from './useChat'
import { useFileContext } from './useFileContext'
import { useHistory } from './useHistory'
import { historyKnowledgeAttachment } from '../utils/sessionHistory'

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
  fileContext: ReturnType<typeof useFileContext>['fileContext']
  historySessions: ReturnType<typeof useHistory>['sessions']
  isLoadingHistory: boolean
  historyError: string | null
  sendMessage: (content: string) => Promise<void>
  stopStreaming: () => void
  clearChatSession: () => void
  loadHistorySession: (sessionId: string) => Promise<void>
  deleteHistorySession: (sessionId: string) => Promise<void>
  deleteAllHistory: () => Promise<void>
  refreshHistory: () => Promise<void>
  setFileContext: (ctx: {
    filename: string
    documentId: string
    ingestionId: string
    retrievalMode: string
  }) => void
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
  const { fileContext, setFileContext, clearFileContext } = useFileContext()
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
    const normalized = firstUser.content.trim().replace(/\n/g, ' ')
    return normalized.length > 80 ? `${normalized.slice(0, 80)}…` : normalized
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

  const loadHistorySession = useCallback(
    async (sessionId: string) => {
      const session = await history.loadSession(sessionId)
      setChartSpec(session.chart_spec)
      chat.loadSession(session)
      const attachment = historyKnowledgeAttachment(session)
      if (attachment) setFileContext(attachment)
      else clearFileContext()
    },
    [chat, clearFileContext, history, setFileContext],
  )

  const sendMessage = useCallback(
    async (content: string) => {
      await chat.sendMessage(
        content,
        selectedModel,
        userName,
        fileContext ? [fileContext.documentId] : undefined,
        systemInstruction,
        ollamaOptions,
        setChartSpec,
      )
      await history.refresh()
    },
    [
      chat,
      fileContext,
      history,
      ollamaOptions,
      selectedModel,
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
    fileContext,
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
    setFileContext,
    clearFileContextSession,
  }
}
