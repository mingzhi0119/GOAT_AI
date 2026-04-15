import { useCallback, useEffect, useMemo, useState } from 'react'
import type {
  ChartSpec,
  HistorySessionDetail,
  OllamaOptionsPayload,
  PersonaSnapshot,
  ThemeStyle,
} from '../api/types'
import { useChat } from './useChat'
import { useFileContext, type FileBindingMode, type FileContextItem } from './useFileContext'
import { loadStoredPersonaSnapshot, persistPersonaSnapshot } from './chatLocalPersistence'
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

interface LockedPersonaState {
  snapshot: PersonaSnapshot
  legacyFallback: boolean
}

function buildDraftPersonaSnapshot(
  themeStyle: ThemeStyle,
  systemInstruction: string,
): PersonaSnapshot {
  return {
    theme_style: themeStyle,
    system_instruction: systemInstruction.trim(),
  }
}

function personaSnapshotsEqual(left: PersonaSnapshot, right: PersonaSnapshot): boolean {
  return (
    left.theme_style === right.theme_style &&
    left.system_instruction === right.system_instruction
  )
}

export interface UseChatSessionReturn {
  messages: ReturnType<typeof useChat>['messages']
  isStreaming: boolean
  sessionId: string | null
  sessionTitle: string | null
  personaStatusMessage: string | null
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
  const draftPersonaSnapshot = useMemo(
    () => buildDraftPersonaSnapshot(themeStyle, systemInstruction),
    [systemInstruction, themeStyle],
  )
  const [lockedPersonaState, setLockedPersonaState] = useState<LockedPersonaState | null>(() => {
    const stored = loadStoredPersonaSnapshot()
    if (!stored || stored.sessionId !== chat.sessionId) return null
    return {
      snapshot: stored.snapshot,
      legacyFallback: stored.legacyFallback,
    }
  })

  const sessionTitle = useSessionTitle({
    sessionId: chat.sessionId,
    messages: chat.messages,
    historySessions: history.sessions,
  })

  useEffect(() => {
    if (!chat.sessionId || !lockedPersonaState) {
      persistPersonaSnapshot(null)
      return
    }
    persistPersonaSnapshot({
      sessionId: chat.sessionId,
      snapshot: lockedPersonaState.snapshot,
      legacyFallback: lockedPersonaState.legacyFallback,
    })
  }, [chat.sessionId, lockedPersonaState])

  const personaStatusMessage = useMemo(() => {
    if (lockedPersonaState?.legacyFallback) {
      return 'This older chat is using a persona snapshot based on your current settings. Start a new chat to apply a different theme or instruction explicitly.'
    }
    if (
      lockedPersonaState &&
      !personaSnapshotsEqual(lockedPersonaState.snapshot, draftPersonaSnapshot)
    ) {
      return 'Theme and instruction changes apply to new chats.'
    }
    return null
  }, [draftPersonaSnapshot, lockedPersonaState])

  const clearLockedPersonaState = useCallback(() => {
    setLockedPersonaState(null)
    persistPersonaSnapshot(null)
  }, [])

  const lockPersonaSnapshot = useCallback(
    (snapshot: PersonaSnapshot, legacyFallback = false) => {
      setLockedPersonaState({ snapshot, legacyFallback })
      return snapshot
    },
    [],
  )

  const resolvePersonaSnapshot = useCallback(
    (sessionId: string) => {
      if (chat.sessionId === sessionId && lockedPersonaState) return lockedPersonaState.snapshot
      return lockPersonaSnapshot(draftPersonaSnapshot, false)
    },
    [chat.sessionId, draftPersonaSnapshot, lockPersonaSnapshot, lockedPersonaState],
  )

  const handleHistorySessionLoaded = useCallback(
    (session: HistorySessionDetail) => {
      if (session.persona_snapshot) {
        lockPersonaSnapshot(session.persona_snapshot, false)
        return
      }
      lockPersonaSnapshot(draftPersonaSnapshot, true)
    },
    [draftPersonaSnapshot, lockPersonaSnapshot],
  )

  const clearChatSession = useCallback(() => {
    chat.clearMessages()
    clearFileContext()
    setChartSpec(null)
    clearLockedPersonaState()
  }, [chat, clearFileContext, clearLockedPersonaState])

  const clearFileContextSession = useCallback(() => {
    clearFileContext()
    chat.clearMessages()
    setChartSpec(null)
    clearLockedPersonaState()
  }, [chat, clearFileContext, clearLockedPersonaState])

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
    onSessionLoaded: handleHistorySessionLoaded,
  })

  const sendMessage = useChatSendMessageController({
    chat,
    history,
    fileContexts,
    selectedModel,
    userName,
    planModeEnabled,
    resolvePersonaSnapshot,
    ollamaOptions,
    setChartSpec,
    setFileContextMode,
  })

  return {
    messages: chat.messages,
    isStreaming: chat.isStreaming,
    sessionId: chat.sessionId,
    sessionTitle,
    personaStatusMessage,
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
