import { useCallback, useState } from 'react'
import type { ChartSpec, OllamaOptionsPayload, ThemeStyle } from '../api/types'
import { useChat } from './useChat'
import { useFileContext, type FileBindingMode, type FileContextItem } from './useFileContext'
import { useHistory } from './useHistory'
import { useChatSendMessageController } from './useChatSendMessageController'
import { useChatSessionHistorySync } from './useChatSessionHistorySync'
import { useSessionTitle } from './useSessionTitle'

interface UseChatSessionArgs {
  selectedModel: string
  userName: string
  systemInstruction: string
  planModeEnabled: boolean
  themeStyle: ThemeStyle
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
  renameHistorySession: (sessionId: string, title: string) => Promise<void>
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
  planModeEnabled,
  themeStyle,
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

  const sessionTitle = useSessionTitle({
    sessionId: chat.sessionId,
    messages: chat.messages,
    historySessions: history.sessions,
  })

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

  const loadHistorySession = useChatSessionHistorySync({
    chat,
    history,
    setChartSpec,
    replaceFileContexts,
    clearFileContext,
  })

  const sendMessage = useChatSendMessageController({
    chat,
    history,
    fileContexts,
    selectedModel,
    userName,
    systemInstruction,
    planModeEnabled,
    themeStyle,
    ollamaOptions,
    setChartSpec,
    setFileContextMode,
  })

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
    renameHistorySession: history.renameSession,
    refreshHistory: history.refresh,
    upsertFileContext,
    setFileContextBindingMode,
    removeFileContext,
    clearFileContextSession,
  }
}
